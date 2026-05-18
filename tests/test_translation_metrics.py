"""Tests for translation_metrics (optional: needs an existing tenjin final/main tree)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_TRACTOR_ROOT = Path(__file__).resolve().parent.parent
_SRC = _TRACTOR_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from translation_metrics import (  # noqa: E402
    composite_translation_score,
    compute_caveman_safety_metrics,
    format_translation_report,
)


class TestTranslationMetrics(unittest.TestCase):
    def test_caveman_on_known_tenjin_output_if_present(self) -> None:
        cargo_main = _TRACTOR_ROOT / "tenjin_results" / "file_1_attempt_1" / "final" / "main"
        if not cargo_main.is_dir():
            self.skipTest("no tenjin_results snapshot")
        m = compute_caveman_safety_metrics(cargo_main)
        self.assertGreater(m["total_fns_count"], 0)
        self.assertIn("total_unsafe_fns_ratio", m)

    def test_format_report_keys(self) -> None:
        m = {
            "rustc_errors": 0,
            "rustc_warnings": 2,
            "clippy_lints": 1,
            "total_fns_count": 10,
            "total_unsafe_fns_count": 1,
            "total_unsafe_fns_ratio": 0.1,
            "files_count": 2,
            "nonempty_lines_count": 50,
        }
        m["composite_translation_score"] = composite_translation_score(m)
        text = format_translation_report(m, title="unit", cargo_check_ok=True)
        self.assertIn("composite score", text.lower())
        self.assertIn("rustc_errors", text)


if __name__ == "__main__":
    unittest.main()
