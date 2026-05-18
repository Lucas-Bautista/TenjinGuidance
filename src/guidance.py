from __future__ import annotations

import argparse
import json
from collections import Counter
import sys
from pathlib import Path
from typing import Any, Iterable
from variable_counts import count_variables, function_return_types, variable_dataflow_sites
from prompt import prompt
from translation_metrics import (
    composite_translation_score,
    format_translation_report,
    static_rust_metrics,
)
import subprocess

_TRACTOR_ROOT = Path(__file__).resolve().parents[1]
_UROP_ROOT = _TRACTOR_ROOT.parent
_TENJIN_CLI = _UROP_ROOT / "tenjin" / "cli"
_GUIDED_RESULTS_ROOT = _TRACTOR_ROOT / "tenjin_results"
_BASELINE_RESULTS_ROOT = _TRACTOR_ROOT / "tenjin_baseline"


def _ensure_tenjin_cli() -> None:
    if not (_TENJIN_CLI / "10j").exists():
        raise FileNotFoundError(
            f"Tenjin CLI not found at {_TENJIN_CLI}. "
            "Expected sibling repo: <parent>/tenjin/ next to TenjinGuidance/"
        )


def _read_codebases_list(codebases_txt: Path) -> list[Path]:
    """
    Reads codebases/codebases.txt: one path per line.
    - blank lines ignored
    - lines starting with '#' ignored
    - relative paths are resolved relative to the codebases.txt directory
    """
    roots: list[Path] = []
    for raw in codebases_txt.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        p = Path(line).expanduser()
        if not p.is_absolute():
            p = (codebases_txt.parent / p)
        roots.append(p.resolve())
    return roots


def _iter_c_files(root: Path) -> Iterable[Path]:
    if root.is_file() and root.suffix == ".c":
        yield root
        return
    if root.is_dir():
        yield from root.rglob("*.c")


def _llm_record_dir(results_dir: Path) -> Path:
    """
    Directory for LLM prompt/response logs, kept *beside* Tenjin's resultsdir so
    ``10j translate`` still sees an empty resultsdir until it runs (Tenjin requires
    empty or ``--reset-resultsdir``).
    """
    return results_dir.parent / f"{results_dir.name}__tractor_llm"


def _run_10j_translate(codebase: Path, resultsdir: Path, guidance: str | None) -> None:
    """
    Runs:
      10j translate --reset-resultsdir --codebase <codebase> --resultsdir <resultsdir>
    """
    cmd = [
        "./10j",
        "translate",
        "--reset-resultsdir",
        "--codebase",
        str(codebase),
        "--resultsdir",
        str(resultsdir),
    ]

    if guidance is not None:
        cmd.extend(["--guidance", guidance])

    print(f"Running command: {' '.join(cmd)}")
    _ensure_tenjin_cli()
    subprocess.run(cmd, check=True, cwd=_TENJIN_CLI)


def _cargo_check(project_dir: Path) -> tuple[bool, str]:
    """
    Runs `cargo check` in project_dir.
    Returns (ok, combined_output).
    """
    proc = subprocess.run(
        ["cargo", "check"],
        cwd=project_dir,
        text=True,
        capture_output=True,
    )
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode == 0, output

# def _as_counter(result: Any) -> Counter:
#     """
#     Normalizes whatever count_variables returns into a Counter.

#     Supported shapes:
#     - Counter
#     - dict-like {key: count}
#     - list of dicts like [{"name":..., "type":..., "occurrences":...}, ...]
#       (used by some evaluation pipelines)
#     """
#     if isinstance(result, Counter):
#         return result

#     if isinstance(result, dict):
#         return Counter(result)

#     if isinstance(result, list):
#         c: Counter = Counter()
#         for item in result:
#             if not isinstance(item, dict):
#                 raise TypeError(f"Unsupported list item from count_variables: {type(item)}")
#             name = item.get("name")
#             typ = item.get("type")
#             occ = item.get("occurrences", 0)
#             c[(name, typ)] += int(occ)
#         return c

#     raise TypeError(f"Unsupported return type from count_variables: {type(result)}")


def _print_counts(file_path: Path, c: Counter, max_items: int | None) -> list[tuple[Any, int]]:
    distinct = len(c)
    total = sum(c.values())

    print(f"\n== {file_path} ==")
    print(f"distinct keys: {distinct}")
    print(f"total occurrences (sum of counts): {total}")

    items = c.most_common()  # sorted by count desc
    if max_items is not None:
        items = items[: max_items]

    for k, v in items:
        print(f"  {k}: {v}")

    return items

def _attempt_root_for_metrics_target(p: Path) -> Path | None:
    """Resolve tenjin_results/.../file_N_attempt_M from final/main or translation_metrics.json."""
    p = p.resolve()
    if p.is_file() and p.name == "translation_metrics.json":
        return p.parent
    if p.is_dir() and p.name.startswith("file_") and "_attempt_" in p.name:
        return p
    if p.is_dir() and p.name == "main" and p.parent.name == "final":
        return p.parent.parent
    return None


def _print_llm_inputs_sidebar(p: Path) -> None:
    """If this metrics path belongs to a guidance attempt, list recorded LLM / guidance files."""
    root = _attempt_root_for_metrics_target(p)
    if root is None:
        return
    candidates: list[Path] = []
    legacy = root / "llm_inputs"
    if legacy.is_dir():
        candidates.append(legacy)
    modern = _llm_record_dir(root)
    if modern.is_dir() and modern not in candidates:
        candidates.append(modern)
    if not candidates:
        return
    print("-" * 72)
    print("LLM inputs & Tenjin guidance (recorded before `10j translate` for this attempt)")
    for llm in candidates:
        names = sorted(f.name for f in llm.iterdir() if f.is_file())
        if not names:
            continue
        print(f"  {llm}")
        for n in names:
            print(f"    {n}")
    print("-" * 72)


def cmd_print_metrics(paths: list[Path], metrics_title: str | None) -> int:
    """
    Print translation metric reports without running the LLM / Tenjin pipeline.

    Each path may be:
      - A Cargo project directory (typically .../final/main) — metrics are recomputed via
        `cargo clippy` and the caveman line scan.
      - A saved translation_metrics.json — metrics are loaded as-is (no clippy rerun);
        composite_score is added if missing.

    When the path matches a guidance run, a footer lists LLM log dirs next to the report:
    ``<attempt>__tractor_llm/`` (current) or legacy ``<attempt>/llm_inputs/``. Open ``*_user.txt``
    for full prompts and ``guidance_to_tenjin.json`` for JSON passed to Tenjin.
    """
    if not paths:
        print("error: pass at least one path after --print-metrics", file=sys.stderr)
        return 2
    for idx, raw in enumerate(paths):
        p = raw.expanduser().resolve()
        if p.is_file() and p.suffix == ".json":
            metrics: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
            if "composite_translation_score" not in metrics:
                metrics["composite_translation_score"] = composite_translation_score(
                    metrics
                )
            title = (
                metrics_title
                if metrics_title and len(paths) == 1
                else f"Saved metrics  ({p})"
            )
            cargo_ok = metrics.get("cargo_check_ok")
            if isinstance(cargo_ok, str):
                cargo_ok = cargo_ok.lower() == "true"
            elif cargo_ok is not None:
                cargo_ok = bool(cargo_ok)
            print(
                format_translation_report(
                    metrics, title=title, cargo_check_ok=cargo_ok
                )
            )
            _print_llm_inputs_sidebar(p)
        elif p.is_dir():
            metrics = static_rust_metrics(p)
            metrics["composite_translation_score"] = composite_translation_score(
                metrics
            )
            title = (
                metrics_title
                if metrics_title and len(paths) == 1
                else f"Fresh metrics  ({p})"
            )
            ok, _ = _cargo_check(p)
            print(
                format_translation_report(metrics, title=title, cargo_check_ok=ok)
            )
            _print_llm_inputs_sidebar(p)
        else:
            print(f"error: not a directory or .json file: {p}", file=sys.stderr)
            return 1
        if idx + 1 < len(paths):
            print()
    return 0


def tenjinize(codebases_txt: Path | None = None) -> int:
    """Run Tenjin on codebases listed in codebases.txt with no LLM guidance."""
    if codebases_txt is None:
        codebases_txt = _TRACTOR_ROOT / "codebases" / "codebases.txt"
    roots = _read_codebases_list(codebases_txt)
    if not roots:
        print(f"No paths found in {codebases_txt}")
        return 0

    print(f"Tractor: baseline Tenjin (no guidance) for {len(roots)} codebase(s).")
    out_root = _BASELINE_RESULTS_ROOT
    for file_num, root in enumerate(roots):
        if not root.exists():
            print(f"[skip] does not exist: {root}")
            continue

        results_dir = out_root / f"file_{file_num}_without_guidance"
        _run_10j_translate(root, results_dir, None)
        print(f"Ran tenjin on {root}")
    return 0

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Tractor: C analysis and Tenjin translation with optional LLM guidance.",
        epilog=(
            "Modes (if none of --guided / --tenjinize-only / --analyze-only is given, --guided is used):\n"
            "  --guided          LLM + Tenjin → tenjin_results/\n"
            "  --tenjinize-only  Tenjin only  → tenjin_baseline/\n"
            "  --analyze-only    Variable counts only, no Tenjin"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--codebases",
        type=Path,
        default=(Path(__file__).resolve().parents[1] / "codebases" / "codebases.txt"),
        help="Path to codebases.txt (default: TenjinGuidance/codebases/codebases.txt)",
    )
    ap.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Only print the top N keys per file (default: print all).",
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--guided",
        action="store_true",
        help="Run the LLM + Tenjin guided translation pipeline.",
    )
    mode.add_argument(
        "--tenjinize-only",
        action="store_true",
        help=(
            "Run Tenjin without LLM guidance (same codebase list as --codebases), then exit."
        ),
    )
    mode.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only print variable counts (no LLM, no Tenjin).",
    )
    ap.add_argument(
        "--print-metrics",
        nargs="+",
        type=Path,
        metavar="PATH",
        help=(
            "Only print translation metric reports, then exit. Each PATH is either a "
            "Cargo tree (e.g. tenjin_results/.../final/main) to recompute, or a "
            "translation_metrics.json file to display saved numbers."
        ),
    )
    ap.add_argument(
        "--metrics-title",
        type=str,
        default=None,
        help="Optional report title when exactly one --print-metrics target is given.",
    )
    args = ap.parse_args()

    _MODE_FLAGS = ("--guided", "--tenjinize-only", "--analyze-only")
    
    if any(f in sys.argv for f in _MODE_FLAGS):
        run_guided = args.guided
        run_analyze_only = args.analyze_only
    else:
        # No mode flag: default to guided (not baseline Tenjin).
        run_guided = True
        run_analyze_only = False

    if args.print_metrics:
        return cmd_print_metrics(list(args.print_metrics), args.metrics_title)

    if args.tenjinize_only:
        print("Tractor mode: baseline Tenjin (--tenjinize-only)", flush=True)
        return tenjinize(args.codebases)

    if run_analyze_only:
        print("Tractor mode: analyze only (--analyze-only)", flush=True)
    elif run_guided:
        print("Tractor mode: guided (LLM + Tenjin)", flush=True)

    codebases_txt: Path = args.codebases
    if not codebases_txt.exists():
        raise FileNotFoundError(f"codebases.txt not found: {codebases_txt}")

    # Read all codebases that we want to run tenjin on
    roots = _read_codebases_list(codebases_txt)
    if not roots:
        print(f"No paths found in {codebases_txt}")
        return 0

    json_out: list[dict[str, Any]] = []

    for root in roots:
        if not root.exists():
            print(f"[skip] does not exist: {root}")
            continue

        for c_file in _iter_c_files(root):
            try:
                counts = count_variables(c_file)
                fn_return_c_types = function_return_types(c_file)
                vdf: dict[str, Any] = variable_dataflow_sites(c_file)
            except Exception as e:
                print(f"[error] {c_file}: {e}")
                continue

            if run_guided:
                # JSON-safe shape: list of entries, keys stringified if needed
                entries = [
                    {"key": str(k), "count": int(v)} for (k, v) in counts.most_common(args.max_items or None)
                ]
                json_out.append(
                    {
                        "file": str(c_file),
                        "codebase": str(root.resolve()),
                        "distinct_keys": int(len(counts)),
                        "total_occurrences": int(sum(counts.values())),
                        "counts": entries,
                        "fn_return_c_types": fn_return_c_types,
                        "variable_dataflow": vdf,
                    }
                )
            else:
                _print_counts(c_file, counts, args.max_items)

    if run_analyze_only:
        return 0

    if not json_out:
        print(
            "error: --guided found no .c files to analyze (check codebases.txt paths).",
            file=sys.stderr,
        )
        return 1

    print(f"Tractor: guided pipeline for {len(json_out)} translation unit(s).")

        # Now we want to prompt the LLM with each file, and its corresponding JSON, and see the corresponding RUST
        # types that it comes up with

    # Each element in JSON out has the shape: {
    #   "file": "path/to/file.c",
    #   "distinct_keys": 123,
    #   "total_occurrences": 456,
    #   "counts": [
    #       {"key": "(function, variable, type)", "count": 10},
    #       ...
    #   ],
    #   "fn_return_c_types": { "function_name": "c_return_type_spelling", ... }
    #   "variable_dataflow": { "func:var" | "GLOBAL:var": { "c_type": str, "sites": [ { "line", "role" }, ... ] } }
    # Prompt used to get the corresponding Rust types for each variable, based on the variable counts JSON that we got from count_variables. We will also have a second prompt to get the mutability of each variable, since that is also important guidance for tenjin.
    type_prompt_path = _TRACTOR_ROOT / "prompts" / "guidance_prompt.txt"
    mut_prompt_path = _TRACTOR_ROOT / "prompts" / "mutability_prompt.txt"
    fn_return_type_prompt_path = _TRACTOR_ROOT / "prompts" / "fn_return_type_prompt.txt"

    # If --guided is not provided, then json_out will be empty and this loop will do nothing, which is fine because the LLM prompting relies on the JSON output to provide it with the variable counts guidance.
   
    # -----------------------------------------------LLM PROMPTING AND TENJIN GUIDANCE LOGIC STARTS HERE------------------------------------------------------
    for file_num, program_info in enumerate(json_out):
        code_sample_path = Path(program_info["file"])
        json_counts = program_info["counts"]  # This is the list of {"key":..., "count":...} dicts
        fn_return_c_types: dict[str, str] = program_info.get("fn_return_c_types", {})
        vdf: dict[str, Any] = program_info.get("variable_dataflow", {})
        # (function, variable, type) is the key, count is the value. We want to pass this information to the LLM so it can use it as guidance for its Rust type inference.
        # variable_dataflow adds per-variable line/role sites (def/ref) for dataflow-consistent type guidance.

        local_variable_counts = []
        global_variable_counts = []

        # Iter
        for entry in json_counts:
            count = entry["count"]
            function, variable_name, variable_type = eval(entry["key"])
            if function == "GLOBAL":
                dkey = f"GLOBAL:{variable_name}"
                row: dict[str, Any] = {
                    "variable_name": variable_name,
                    "type": variable_type,
                    "count": count,
                }
            else:
                dkey = f"{function}:{variable_name}"
                row = {
                    "variable_name": dkey,
                    "type": variable_type,
                    "count": count,
                }
            sites = (vdf.get(dkey) or {}).get("sites")
            if sites is not None:
                row["dataflow_sites"] = sites
            if function == "GLOBAL":
                global_variable_counts.append(row)
            else:
                local_variable_counts.append(row)

        print(f"local variable Counts {local_variable_counts}")

        compile_errors: str | None = None
        for attempt in range(1, 4):
            results_dir = _GUIDED_RESULTS_ROOT / f"file_{file_num}_attempt_{attempt}"
            llm_record_dir = _llm_record_dir(results_dir)

            local_variable_counts_str = json.dumps(local_variable_counts, indent=2, sort_keys=False)
            global_variable_counts_str = json.dumps(global_variable_counts, indent=2, sort_keys=False)

            # We are going to pass in the code that we want to get the Rust types from, the prompt that tells the LLM how to format its response, and the JSON data that has the variable counts for that code,
            # and we want the LLM to respond with a list of variable names, their types, and their counts, which we will then parse and use as guidance for tenjin.
            local_variable_responses = prompt(
                code_sample_path,
                type_prompt_path,
                local_variable_counts_str,
                compile_errors,
                record_dir=llm_record_dir,
                record_name="01_types_local",
            )
            global_variable_responses = prompt(
                code_sample_path,
                type_prompt_path,
                global_variable_counts_str,
                compile_errors,
                record_dir=llm_record_dir,
                record_name="02_types_global",
            )
            is_mutable_responses = prompt(
                code_sample_path,
                mut_prompt_path,
                local_variable_counts_str,
                compile_errors,
                record_dir=llm_record_dir,
                record_name="03_mutability",
            )  # we can reuse the same counts JSON for this second prompt, since it also just asks about variable mutability

            fn_return_c_json = json.dumps(fn_return_c_types, indent=2, sort_keys=False)
            if fn_return_c_types:
                fn_return_type_responses = prompt(
                    code_sample_path,
                    fn_return_type_prompt_path,
                    fn_return_c_json,
                    compile_errors,
                    data_heading="Function return types (C, from clang)",
                    json_key="fn_return_c_types",
                    record_dir=llm_record_dir,
                    record_name="04_fn_return_type",
                )
                _raw = fn_return_type_responses[0][1]
                if isinstance(_raw, dict):
                    fn_return_type: dict[str, str] = {str(k): str(v) for k, v in _raw.items()}
                else:
                    print(
                        f"[warn] {code_sample_path}: expected JSON object for fn_return_type, got {type(_raw).__name__}; using empty dict"
                    )
                    fn_return_type = {}
            else:
                fn_return_type = {}

            print(f"Local Variable Counts for {code_sample_path}:\n{local_variable_counts}\n\n")
            print(f"Global Variable Counts for {code_sample_path}:\n{global_variable_counts}\n\n")
            print(f"Mutablility Responses for {code_sample_path}:\n{is_mutable_responses}\n\n")
            print(f"fn_return_type (Rust) for {code_sample_path}:\n{fn_return_type}\n\n")


            # TODO: THIS ONLY WORKS BECAUSE WE ARE DEALING WITH A SINGULAR MODEL, OTHERWISE WE WOULD NEED TO MATCH THE RESPONSES TO THE MODELS. WE CAN ADD THIS LATER IF WE WANT TO RUN MULTIPLE MODELS.
            for model, response in local_variable_responses:
                print("response:", response, "\n\n")
                vars_of_type = {}  # This is the dict we will eventually pass to tenjin as guidance, after we populate it with the LLM's responses
                for variable, rust_type in response.items():
                    # print(f"Model {model} guessed variable {variable} has Rust type {rust_type}\n")
                    if vars_of_type.get(str(rust_type)) is not None:
                        existing = vars_of_type[str(rust_type)]
                        if type(existing) == list:
                            existing.append(variable)
                        else:
                            vars_of_type[str(rust_type)] = [existing, variable]
                    else:
                        vars_of_type[str(rust_type)] = variable      
                print(f"Guidance dict so far: {vars_of_type}\n\n")

            for model, response in global_variable_responses:
                print("response:", response, "\n\n")
                declspecs_of_type = {}  # This is the dict we will eventually pass to tenjin as guidance, after we populate it with the LLM's responses
                for variable, rust_type in response.items():
                    # print(f"Model {model} guessed variable {variable} has Rust type {rust_type}\n")
                    if declspecs_of_type.get(str(rust_type)) is not None:
                        existing = declspecs_of_type[str(rust_type)]
                        if type(existing) == list:
                            existing.append(variable)
                        else:
                            declspecs_of_type[str(rust_type)] = [existing, variable]
                    else:
                        declspecs_of_type[str(rust_type)] = variable      
                print(f"Declspecs dict so far: {declspecs_of_type}\n\n")


            guidance = {
                "vars_of_type": vars_of_type,
                "declspecs_of_type": declspecs_of_type,
                "vars_mut": is_mutable_responses[0][1],  # again, this only works because we are dealing with a singular model. If we had multiple models, we would need to match the mutability responses to the correct model and incorporate that into the guidance dict in a way that tenjin can understand.
                "fn_return_type": fn_return_type,
            }

            print(f"Final guidance dict for {code_sample_path}:\n{json.dumps(guidance, indent=2, sort_keys=False)}\n\n")

            llm_record_dir.mkdir(parents=True, exist_ok=True)
            (llm_record_dir / "guidance_to_tenjin.json").write_text(
                json.dumps(guidance, indent=2, sort_keys=False), encoding="utf-8"
            )
            if compile_errors:
                (llm_record_dir / "compile_errors_in_prompt.txt").write_text(
                    compile_errors, encoding="utf-8"
                )

            # This function wil run tenjin with the provided guidance (the variable counts and the LLM's inferred Rust types based on those counts), and save the results in a separate directory for each file.
            _run_10j_translate(Path(program_info["codebase"]), results_dir, json.dumps(guidance, indent=2, sort_keys=False))

            cargo_dir = results_dir / "final" / "main"
            if not cargo_dir.exists():
                compile_errors = f"cargo directory not found: {cargo_dir}"
                print(f"[attempt {attempt}] {compile_errors}")
                continue

            ok, output = _cargo_check(cargo_dir)
            metrics_summary: dict[str, Any] = {}
            try:
                metrics = static_rust_metrics(cargo_dir)
                metrics["composite_translation_score"] = composite_translation_score(metrics)
                metrics["cargo_check_ok"] = ok
                metrics_summary = dict(metrics)
                metrics_path = results_dir / "translation_metrics.json"
                metrics_path.write_text(
                    json.dumps(metrics_summary, indent=2, sort_keys=False, default=str),
                    encoding="utf-8",
                )
                title = f"Translation metrics  (file_{file_num} attempt {attempt})  {cargo_dir.name}"
                report = format_translation_report(
                    metrics, title=title, cargo_check_ok=ok
                )
                print(report)
            except Exception as ex:
                print(f"[attempt {attempt}] translation metrics skipped: {ex}")

            if ok:
                print(f"[attempt {attempt}] cargo check OK for {cargo_dir}")
                break

            compile_errors = output
            if cargo_dir.exists():
                err_path = llm_record_dir / "cargo_check_stderr.txt"
                err_path.write_text(output, encoding="utf-8")
            print(f"[attempt {attempt}] cargo check failed for {cargo_dir}\n{output}")
        else:
            print(f"[give up] cargo check failed after 3 attempts for {code_sample_path}")

        # vars_of_type_tenjin_json = json.dumps(vars_of_type, indent=2, sort_keys=False)
        # declspecs_of_type_tenjin_json = json.dumps(declspecs_of_type, indent=2, sort_keys=False)
    # After we get these RUST types, we can run tenjin with guidance.


    '''
    10j translate has an optional parameter called --guidance. It can be either a JSON literal or a filepath, whose contents should be a JSON object. The following keys are available:

    vars_of_type - a dict with keys as serialized Rust type strings. The value for each key is either a variable specifier, or a list of specifiers. A variable specifier is a string like
    foo:bar, which indicates the bar parameter or local variable within the foo function.

    fn_return_type - function name to Rust return type (syn syntax); from the LLM; consumed by tenjin.
    '''

    return 0


if __name__ == "__main__":
    raise SystemExit(main())