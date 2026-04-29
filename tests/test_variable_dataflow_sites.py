"""
Tests for variable_counts.variable_dataflow_sites (clang def/ref roles).

Requires macOS + Homebrew libclang (same as other Tractor clang tests).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_TRACTOR_ROOT = Path(__file__).resolve().parent.parent
_SRC = _TRACTOR_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from variable_counts import variable_dataflow_sites  # noqa: E402


def _roles(df: dict, key: str) -> list[str]:
    return [s["role"] for s in df[key]["sites"]]


@unittest.skipUnless(sys.platform == "darwin", "variable_dataflow_sites needs xcrun + macOS SDK")
class TestVariableDataflowSites(unittest.TestCase):
    def test_assign_and_compound_and_global(self) -> None:
        p = _TRACTOR_ROOT / "tests" / "fixtures" / "dataflow_assign.c"
        df = variable_dataflow_sites(str(p))
        self.assertEqual(df["main:x"]["c_type"], "int")
        self.assertEqual(
            df["main:x"]["sites"],
            [
                {"line": 6, "role": "decl"},
                {"line": 7, "role": "write"},
                {"line": 8, "role": "write"},
                {"line": 9, "role": "read"},
            ],
        )
        self.assertEqual(df["GLOBAL:counter"]["c_type"], "int")
        self.assertEqual(
            df["GLOBAL:counter"]["sites"],
            [
                {"line": 3, "role": "decl"},
                {"line": 9, "role": "write"},
                {"line": 10, "role": "read"},
            ],
        )

    def test_prototype_param_excluded(self) -> None:
        p = _TRACTOR_ROOT / "tests" / "fixtures" / "return_types_sample.c"
        df = variable_dataflow_sites(str(p))
        self.assertNotIn("only_prototype:x", df)

    def test_param_and_return_read(self) -> None:
        p = _TRACTOR_ROOT / "tests" / "fixtures" / "return_types_sample.c"
        df = variable_dataflow_sites(str(p))
        self.assertEqual(_roles(df, "with_proto_then_def:x"), ["param", "read"])

    def test_edge_pair_addr_parameter_and_use(self) -> None:
        p = _TRACTOR_ROOT / "tests" / "fixtures" / "return_types_edge.c"
        df = variable_dataflow_sites(str(p))
        self.assertEqual(df["pair_addr:p"]["c_type"], "const struct pair *")
        self.assertEqual(_roles(df, "pair_addr:p"), ["param", "read"])

    def test_edge_inline_two_params(self) -> None:
        p = _TRACTOR_ROOT / "tests" / "fixtures" / "return_types_edge.c"
        df = variable_dataflow_sites(str(p))
        self.assertEqual(_roles(df, "inline_add:x"), ["param", "read"])
        self.assertEqual(_roles(df, "inline_add:y"), ["param", "read"])

    def test_complex_local_struct_and_global(self) -> None:
        p = _TRACTOR_ROOT / "tests" / "fixtures" / "return_types_complex.c"
        df = variable_dataflow_sites(str(p))
        self.assertEqual(df["returns_thing:t"]["c_type"], "thing_t")
        self.assertEqual(
            _roles(df, "returns_thing:t"),
            ["decl", "read", "read"],
        )
        self.assertIn("GLOBAL:g_volatile_ptr", df)
        self.assertEqual(_roles(df, "GLOBAL:g_volatile_ptr"), ["decl", "read"])

    def test_gcd_main_loop_index(self) -> None:
        p = _TRACTOR_ROOT / "c_samples" / "02_gcd_lcm.c"
        self.assertTrue(p.is_file())
        df = variable_dataflow_sites(str(p))
        self.assertIn("main:i", df)
        roles = _roles(df, "main:i")
        self.assertIn("decl", roles)
        self.assertIn("write", roles)
        self.assertGreaterEqual(roles.count("read"), 2)


if __name__ == "__main__":
    unittest.main()
