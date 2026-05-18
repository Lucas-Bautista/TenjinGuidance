"""
Static Rust quality metrics for a translated Cargo project (TenjinGuidance-side).

Logic mirrors Tenjin's cli/static_measurements_rust.py (caveman line scan +
`cargo clippy --message-format=json`) without importing Tenjin's hermetic stack,
so it runs from the TenjinGuidance repo with a normal `cargo` on PATH.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def compute_caveman_safety_metrics(cargo_project_dir: Path) -> dict[str, int | float]:
    """Line-based counts of Rust functions and `unsafe fn` occurrences."""
    files_count = 0
    file_lines_count = 0
    total_fns_count = 0
    total_unsafe_fns_count = 0

    def process_file(file_path: Path) -> None:
        nonlocal files_count, file_lines_count, total_fns_count, total_unsafe_fns_count

        if file_path == cargo_project_dir / "build.rs":
            return
        files_count += 1
        text = file_path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            line = line.rstrip()
            if not line:
                continue
            file_lines_count += 1
            if "fn " in line and "(" in line:
                if line.endswith(";"):
                    continue
                total_fns_count += 1
                if "unsafe " in line:
                    total_unsafe_fns_count += 1

    for file_path in cargo_project_dir.glob("**/*.rs"):
        if file_path.is_file():
            process_file(file_path)

    if total_fns_count == 0:
        return {
            "total_fns_count": 0,
            "total_unsafe_fns_count": 0,
            "total_unsafe_fns_ratio": 0.0,
            "files_count": files_count,
            "nonempty_lines_count": file_lines_count,
            "caveman_error": "No functions matched the heuristic scan",
        }

    ratio = round(total_unsafe_fns_count / total_fns_count, 3)
    return {
        "total_fns_count": total_fns_count,
        "total_unsafe_fns_count": total_unsafe_fns_count,
        "total_unsafe_fns_ratio": ratio,
        "files_count": files_count,
        "nonempty_lines_count": file_lines_count,
    }


def get_clippy_messages_json(
    cargo_project_dir: Path,
) -> tuple[list[dict[str, Any]], subprocess.CompletedProcess]:
    manifest = (cargo_project_dir / "Cargo.toml").resolve()
    cmd = [
        "cargo",
        "clippy",
        "--message-format",
        "json",
        "--manifest-path",
        manifest.as_posix(),
        "--",
        "-Aclippy::missing_safety_doc",
        "-Aclippy::too_many_arguments",
        "-Aclippy::absurd_extreme_comparisons",
    ]
    res = subprocess.run(
        cmd,
        cwd=cargo_project_dir,
        text=True,
        capture_output=True,
    )
    messages: list[dict[str, Any]] = []
    for line in (res.stdout or "").split("\n"):
        if not line or line[0] != "{":
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("reason") != "compiler-message":
            continue
        messages.append(obj)
    return messages, res


def count_rustc_and_clippy_lints(cargo_project_dir: Path) -> dict[str, int]:
    rustc_errors = 0
    rustc_warnings = 0
    clippy_lints = 0

    messages, res = get_clippy_messages_json(cargo_project_dir)
    if res.returncode != 0:
        rustc_errors += 1

    for obj in messages:
        message = obj["message"]
        mb_code = message.get("code")
        level = message.get("level")

        if mb_code:
            kind = mb_code["code"]
            if isinstance(kind, str) and kind.startswith("clippy::"):
                clippy_lints += 1
            else:
                if level == "error":
                    rustc_errors += 1
                elif level == "warning":
                    rustc_warnings += 1

    return {
        "rustc_errors": rustc_errors,
        "rustc_warnings": rustc_warnings,
        "clippy_lints": clippy_lints,
    }


def static_rust_metrics(cargo_project_dir: Path) -> dict[str, int | float | str]:
    """Compute static measurements for a Rust project directory (e.g. final/main)."""
    if not cargo_project_dir.is_dir():
        raise NotADirectoryError(cargo_project_dir)

    cave = compute_caveman_safety_metrics(cargo_project_dir)
    lints = count_rustc_and_clippy_lints(cargo_project_dir)
    out: dict[str, int | float | str] = {**cave, **lints}
    return out


def composite_translation_score(m: dict[str, int | float | str]) -> float:
    """
    Rough 0..100 heuristic: higher is better. Experimental — tune weights for your goals.

    Penalizes rustc errors heavily, then clippy noise, warnings, and unsafe-fn ratio.
    """
    if m.get("caveman_error"):
        return 0.0
    errors = int(m.get("rustc_errors", 0))
    warnings = int(m.get("rustc_warnings", 0))
    clippy = int(m.get("clippy_lints", 0))
    unsafe_ratio = float(m.get("total_unsafe_fns_ratio", 0.0))

    score = 100.0
    score -= errors * 25.0
    score -= min(warnings * 0.5, 20.0)
    score -= min(clippy * 0.25, 20.0)
    score -= unsafe_ratio * 45.0
    return max(0.0, min(100.0, round(score, 1)))


def format_translation_report(
    metrics: dict[str, int | float | str],
    *,
    title: str,
    cargo_check_ok: bool | None = None,
) -> str:
    """Human-readable block for stdout or logs."""
    lines: list[str] = []
    w = 26
    sep = "=" * 72
    lines.append(sep)
    lines.append(title)
    lines.append(sep)
    if cargo_check_ok is not None:
        lines.append(f"{'cargo check':{w}}{'OK' if cargo_check_ok else 'FAILED'}")
    if metrics.get("caveman_error"):
        lines.append(f"{'caveman scan':{w}}{metrics['caveman_error']}")
    else:
        lines.append(f"{'composite score (0-100)':{w}}{composite_translation_score(metrics)}")
    lines.append("-" * 72)
    order = [
        "rustc_errors",
        "rustc_warnings",
        "clippy_lints",
        "total_fns_count",
        "total_unsafe_fns_count",
        "total_unsafe_fns_ratio",
        "files_count",
        "nonempty_lines_count",
    ]
    for k in order:
        if k in metrics:
            lines.append(f"{k:{w}}{metrics[k]}")
    lines.append(sep)
    return "\n".join(lines)
