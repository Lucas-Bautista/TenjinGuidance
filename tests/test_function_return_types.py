"""
Unit tests for variable_counts.function_return_types.

They require a macOS SDK (xcrun) and libclang at the path in variable_counts.Config
(the same as normal Tractor / clang use).

Tests for `return_types_complex.c` and `return_types_edge.c` compare the full
mapping to exact spelling strings from libclang; if Apple LLVM updates pretty-
printing, adjust those expected dicts.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_TRACTOR_ROOT = Path(__file__).resolve().parent.parent
_SRC = _TRACTOR_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from variable_counts import function_return_types  # noqa: E402


@unittest.skipUnless(sys.platform == "darwin", "function_return_types uses xcrun + macOS SDK")
class TestFunctionReturnTypes(unittest.TestCase):
    def test_fixture_includes_only_definitions(self) -> None:
        path = _TRACTOR_ROOT / "tests" / "fixtures" / "return_types_sample.c"
        got = function_return_types(str(path))

        self.assertIn("with_proto_then_def", got, msg="definition should be recorded")
        self.assertIn("main", got)
        self.assertIn("returns_void", got)
        self.assertIn("static_helper", got)

        # Prototype with no body must not be treated as a definition.
        self.assertNotIn("only_prototype", got)

        self.assertEqual(got["with_proto_then_def"], "int")
        self.assertEqual(got["main"], "int")
        self.assertEqual(got["returns_void"], "void")
        self.assertEqual(got["static_helper"], "long")

    def test_gcd_sample_main_returns_int(self) -> None:
        path = _TRACTOR_ROOT / "c_samples" / "02_gcd_lcm.c"
        self.assertTrue(path.is_file(), msg=f"missing sample: {path}")
        got = function_return_types(str(path))
        self.assertEqual(got, {"main": "int"})

    def test_complex_fixture(self) -> None:
        path = _TRACTOR_ROOT / "tests" / "fixtures" / "return_types_complex.c"
        got = function_return_types(str(path))
        self.assertEqual(
            got,
            {
                "big_counter": "unsigned long long",
                "bytes_for": "size_t",
                "cvp": "const void *",
                "dprod": "double",
                "flag_is_set": "_Bool",
                "fsum": "float",
                "get_binop": "int (*)(int, int)",
                "int_ptr": "int *",
                "main": "int",
                "malloc_like": "void *",
                "pick_color": "enum color",
                "read_u32": "uint32_t",
                "returns_struct": "struct point",
                "returns_thing": "thing_t",
                "volatile_get": "volatile int *",
            },
        )

    def test_edge_fixture(self) -> None:
        path = _TRACTOR_ROOT / "tests" / "fixtures" / "return_types_edge.c"
        got = function_return_types(str(path))
        self.assertEqual(
            got,
            {
                "alloc_block": "int *restrict",
                "as_number": "number_t",
                "inline_add": "int",
                "main": "int",
                "pair_addr": "const struct pair *",
            },
        )

if __name__ == "__main__":
    unittest.main()
