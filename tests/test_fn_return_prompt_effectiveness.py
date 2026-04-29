"""
Live integration: compare clang C return types vs the LLM’s `fn_return_type` prompt (Rust).

Requires:
  - macOS (libclang + xcrun, same as variable_counts)
  - ANTHROPIC_API_KEY: in the environment or `Tractor/.env` (python-dotenv on import)
  - TRACTOR_RUN_LIVE_LLM=1 so `unittest discover` does not call the API unless you opt in

Run and read stdout (opt-in live LLM):
  cd Tractor && TRACTOR_RUN_LIVE_LLM=1 .venv/bin/python -m unittest tests.test_fn_return_prompt_effectiveness -v
  cd Tractor && .venv/bin/python tests/test_fn_return_prompt_effectiveness.py
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from dotenv import load_dotenv

_TRACTOR_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_TRACTOR_ROOT / ".env")
load_dotenv()

_SRC = _TRACTOR_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

FN_RETURN_PROMPT = _TRACTOR_ROOT / "prompts" / "fn_return_type_prompt.txt"

_LIVE = (
    sys.platform == "darwin"
    and bool(os.environ.get("ANTHROPIC_API_KEY"))
    and os.environ.get("TRACTOR_RUN_LIVE_LLM") == "1"
)


def _print_c_vs_rust_table(
    c_path: Path, label: str, *, c_types: dict[str, str] | None = None
) -> dict[str, str]:
    """
    Call the LLM with the same contract as guidance.py, then print a comparison table.
    `prompt` also logs raw model output to stdout.
    """
    from prompt import prompt
    from variable_counts import function_return_types

    c_path = c_path.resolve()
    if c_types is None:
        c_types = function_return_types(str(c_path))
    c_json = json.dumps(c_types, indent=2, sort_keys=True)

    responses = prompt(
        c_path,
        FN_RETURN_PROMPT,
        c_json,
        None,
        data_heading="Function return types (C, from clang)",
        json_key="fn_return_c_types",
    )
    rust_by_fn: dict[str, str] = {}
    for _model, data in responses:
        if isinstance(data, dict):
            for k, v in data.items():
                rust_by_fn[str(k)] = str(v)
        # With one model, take first dict-shaped batch only; matches guidance.py
        break

    names = sorted(set(c_types) | set(rust_by_fn))
    w = max((len(n) for n in names), default=0)
    w = max(w, 12)

    print()
    print("=" * 72)
    print(label)
    print("=" * 72)
    print(f"{'function':{w}}  {'C (clang)':<34}  {'Rust (LLM)'}")
    print("-" * 72)
    for name in names:
        c = c_types.get(name, "—")
        r = rust_by_fn.get(name, "—")
        print(f"{name:{w}}  {c:<34}  {r}")
    print("=" * 72)
    print(
        f"  C type keys: {len(c_types)}  |  Rust (LLM) keys: {len(rust_by_fn)}"
        f"  |  matched names: {len(set(c_types) & set(rust_by_fn))}"
    )
    print()
    return rust_by_fn


@unittest.skipUnless(
    _LIVE,
    "Set TRACTOR_RUN_LIVE_LLM=1 and ANTHROPIC_API_KEY on macOS to run live fn_return_type prompt tests",
)
class TestFnReturnPromptEffectiveness(unittest.TestCase):
    def test_print_fixture_sample_c(self) -> None:
        from variable_counts import function_return_types

        c_file = _TRACTOR_ROOT / "tests" / "fixtures" / "return_types_sample.c"
        self.assertTrue(c_file.is_file())
        c_types = function_return_types(str(c_file))
        _print_c_vs_rust_table(
            c_file,
            "return_types_sample.c: C return types (clang) vs Rust (LLM fn_return_type prompt)",
            c_types=c_types,
        )
        self.assertIn("main", c_types)

    def test_print_gcd_sample_c(self) -> None:
        from variable_counts import function_return_types

        c_file = _TRACTOR_ROOT / "c_samples" / "02_gcd_lcm.c"
        self.assertTrue(c_file.is_file())
        c_types = function_return_types(str(c_file))
        _print_c_vs_rust_table(
            c_file,
            "02_gcd_lcm.c: C return types (clang) vs Rust (LLM fn_return_type prompt)",
            c_types=c_types,
        )
        self.assertEqual(c_types.get("main"), "int")


if __name__ == "__main__":
    if sys.platform == "darwin" and not os.environ.get("ANTHROPIC_API_KEY"):
        from variable_counts import function_return_types

        p = _TRACTOR_ROOT / "tests" / "fixtures" / "return_types_sample.c"
        if p.is_file():
            print("No ANTHROPIC_API_KEY: only clang C return map (set key for full LLM comparison):")
            print(" ", function_return_types(str(p.resolve())))
            print()
    unittest.main()
