from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from variable_counts import count_variables 
from prompt import prompt
import subprocess

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


def _run_10j_translate(codebase: Path, resultsdir: Path, guidance: str) -> None:
    """
    Runs:
      10j translate --codebase <codebase> --resultsdir <resultsdir>
    """
    cmd = [
        "./10j",
        "translate",
        "--codebase",
        str(codebase),
        "--resultsdir",
        str(resultsdir),
    ]

    if guidance is not None:
        cmd.extend(["--guidance", guidance])

    print(f"Running command: {' '.join(cmd)}")
    # check=True -> raises CalledProcessError if 10j fails
    subprocess.run(cmd, check=True, cwd=Path("/Users/lucasbautista/Documents/UROP/tenjin/cli"))

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

def tenjinize():
    # We run tenjin on all the files inside of the codebases: no guidance
    codebases_txt = Path("/Users/lucasbautista/Documents/UROP/Tractor/codebases/codebases.txt")
    roots = _read_codebases_list(codebases_txt)
    if not roots:
        print(f"No paths found in {codebases_txt}")
        return 0
    
    for file_num, root in enumerate(roots):
        if not root.exists():
            print(f"[skip] does not exist: {root}")
            continue

        _run_10j_translate(str(root), Path(f"/Users/lucasbautista/Documents/UROP/Tractor/tenjin_results/file_{file_num}_without_guidance"), None)

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run variable counts over all .c files under paths listed in codebases/codebases.txt."
    )
    ap.add_argument(
        "--codebases",
        type=Path,
        default=(Path(__file__).resolve().parents[1] / "codebases" / "codebases.txt"),
        help="Path to codebases.txt (default: Tractor/codebases/codebases.txt)",
    )
    ap.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Only print the top N keys per file (default: print all).",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )
    args = ap.parse_args()

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
            except Exception as e:
                print(f"[error] {c_file}: {e}")
                continue

            if args.json:
                # JSON-safe shape: list of entries, keys stringified if needed
                entries = [
                    {"key": str(k), "count": int(v)} for (k, v) in counts.most_common(args.max_items or None)
                ]
                json_out.append(
                    {
                        "file": str(c_file),
                        "distinct_keys": int(len(counts)),
                        "total_occurrences": int(sum(counts.values())),
                        "counts": entries,
                    }
                )
            else:
                listed = _print_counts(c_file, counts, args.max_items)

        if args.json:
            print(json.dumps(json_out, indent=2, sort_keys=False))

        # Now we want to prompt the LLM with each file, and its corresponding JSON, and see the corresponding RUST
        # types that it comes up with

    # Each element in JSON out has the shape: {
    #   "file": "path/to/file.c",
    #   "distinct_keys": 123,
    #   "total_occurrences": 456,
    #   "counts": [
    #       {"key": "(function, variable, type)", "count": 10},
    #       ...
    #   ]
    # Prompt used to get the corresponding Rust types for each variable, based on the variable counts JSON that we got from count_variables. We will also have a second prompt to get the mutability of each variable, since that is also important guidance for tenjin.
    type_prompt_path = Path("../prompts/guidance_prompt.txt")

    # Prompt used to get the mutability of each variable, since that is also important guidance for tenjin. We can reuse the same variable counts JSON for this second prompt, since it also just asks about variable mutability and doesn't require any different information than the first prompt. 
    # This is separate from the type_prompt because we want to keep the guidance as modular as possible, so that we can easily add new types of guidance in the future without having to change the existing prompts or the way we call them. For example, if we wanted to add a prompt that asks about 
    # variable lifetimes, we could just create a new lifetime_prompt.txt and call prompt() with that new prompt and the same counts JSON.
    mut_prompt_path = Path("../prompts/mutability_prompt.txt")

    # If --json is not provided, then json_out will be empty and this loop will do nothing, which is fine because the LLM prompting relies on the JSON output to provide it with the variable counts guidance.
   
    # -----------------------------------------------LLM PROMPTING AND TENJIN GUIDANCE LOGIC STARTS HERE------------------------------------------------------
    for file_num, program_info in enumerate(json_out):
        code_sample_path = Path(program_info["file"])
        json_counts = program_info["counts"]  # This is the list of {"key":..., "count":...} dicts
        # (function, variable, type) is the key, count is the value. We want to pass this information to the LLM so it can use it as guidance for its Rust type inference.

        local_variable_counts = []
        global_variable_counts = []

        # Iter
        for entry in json_counts:
            count = entry["count"]
            function, variable_name, variable_type = eval(entry["key"])
            if function == "GLOBAL":
                global_variable_counts.append({
                    "variable_name": variable_name,
                    "type": variable_type,
                    "count": count
                })
            else:
                local_variable_counts.append({
                    "variable_name": f"{function}:{variable_name}",
                    "type": variable_type,
                    "count": count
                })

        print(f"local variable Counts {local_variable_counts}")
        local_variable_counts_str = json.dumps(local_variable_counts, indent=2, sort_keys=False)
        global_variable_counts_str = json.dumps(global_variable_counts, indent=2, sort_keys=False)

        # We are going to pass in the code that we want to get the Rust types from, the prompt that tells the LLM how to format its response, and the JSON data that has the variable counts for that code, a
        # and we want the LLM to respond with a list of variable names, their types, and their counts, which we will then parse and use as guidance for tenjin.
        local_variable_responses = prompt(code_sample_path, type_prompt_path, local_variable_counts_str)
        global_variable_responses = prompt(code_sample_path, type_prompt_path, global_variable_counts_str)
        is_mutable_responses = prompt(code_sample_path, mut_prompt_path, local_variable_counts_str)  # we can reuse the same counts JSON for this second prompt, since it also just asks about variable mutability

        print(f"Local Variable Counts for {code_sample_path}:\n{local_variable_counts}\n\n")
        print(f"Global Variable Counts for {code_sample_path}:\n{global_variable_counts}\n\n")
        print(f"Mutablility Responses for {code_sample_path}:\n{is_mutable_responses}\n\n")


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
            "vars_mut": is_mutable_responses[0][1]  # again, this only works because we are dealing with a singular model. If we had multiple models, we would need to match the mutability responses to the correct model and incorporate that into the guidance dict in a way that tenjin can understand.
        }

        print(f"Final guidance dict for {code_sample_path}:\n{json.dumps(guidance, indent=2, sort_keys=False)}\n\n")

        # This function wil run tenjin with the provided guidance (the variable counts and the LLM's inferred Rust types based on those counts), and save the results in a separate directory for each file.
        _run_10j_translate(program_info["file"], Path(f"/Users/lucasbautista/Documents/UROP/Tractor/tenjin_results/file_{file_num}"), json.dumps(guidance, indent=2, sort_keys=False))

        # vars_of_type_tenjin_json = json.dumps(vars_of_type, indent=2, sort_keys=False)
        # declspecs_of_type_tenjin_json = json.dumps(declspecs_of_type, indent=2, sort_keys=False)
    # After we get these RUST types, we can run tenjin with guidance.


    '''
    10j translate has an optional parameter called --guidance. It can be either a JSON literal or a filepath, whose contents should be a JSON object. The following keys are available:

    vars_of_type - a dict with keys as serialized Rust type strings. The value for each key is either a variable specifier, or a list of specifiers. A variable specifier is a string like 
    foo:bar, which indicates the bar parameter or local variable within the foo function.
    '''

    return 0


if __name__ == "__main__":
    raise SystemExit(main())