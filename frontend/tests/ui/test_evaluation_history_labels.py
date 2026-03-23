import unittest
from datetime import UTC, datetime

from components.shared.evaluation_history_labels import (
    build_benchmark_history_entry_label,
    format_benchmark_run_selector_label,
)


class TestBuildBenchmarkHistoryEntryLabel(unittest.TestCase):
    def test_datetime_run_id_and_settings(self) -> None:
        dt = datetime(2025, 3, 1, 14, 30, 0, tzinfo=UTC)
        lab = build_benchmark_history_entry_label(
            generated_at=dt,
            run_id="abcdef123456",
            enable_query_rewrite=True,
            enable_hybrid_retrieval=False,
            fallback_run_number=1,
        )
        self.assertIn("2025-03-01 14:30 UTC", lab)
        self.assertIn("abcdef123456", lab)
        self.assertIn("query rewrite on", lab)
        self.assertIn("hybrid off", lab)

    def test_fallback_run_number_when_empty(self) -> None:
        lab = build_benchmark_history_entry_label(
            generated_at=None,
            run_id=None,
            enable_query_rewrite=None,
            enable_hybrid_retrieval=None,
            fallback_run_number=3,
        )
        self.assertEqual(lab, "run 3")

    def test_settings_only_no_timestamp(self) -> None:
        lab = build_benchmark_history_entry_label(
            generated_at=None,
            run_id=None,
            enable_query_rewrite=False,
            enable_hybrid_retrieval=True,
            fallback_run_number=1,
        )
        self.assertEqual(lab, "query rewrite off · hybrid on")

    def test_string_generated_at_truncated(self) -> None:
        long_ts = "x" * 50
        lab = build_benchmark_history_entry_label(
            generated_at=long_ts,
            run_id="rid",
            enable_query_rewrite=None,
            enable_hybrid_retrieval=None,
            fallback_run_number=1,
        )
        self.assertTrue(lab.startswith("x" * 32))


class TestFormatBenchmarkRunSelectorLabel(unittest.TestCase):
    def test_uses_stored_label_and_short_id(self) -> None:
        s = format_benchmark_run_selector_label(
            {"label": "Morning run", "run_id": "abcdefghijk"},
            index=0,
        )
        self.assertIn("Morning run", s)
        self.assertIn("abcdefgh…", s)

    def test_missing_label_uses_index(self) -> None:
        s = format_benchmark_run_selector_label({"run_id": "short"}, index=2)
        self.assertIn("Run 3", s)
        self.assertIn("short", s)

    def test_appends_qr_hyb_only_when_both_bool(self) -> None:
        with_qr_hy = format_benchmark_run_selector_label(
            {
                "label": "L",
                "run_id": "r1",
                "enable_query_rewrite": True,
                "enable_hybrid_retrieval": False,
            },
            0,
        )
        self.assertIn("QR on", with_qr_hy)
        self.assertIn("Hyb off", with_qr_hy)

        partial = format_benchmark_run_selector_label(
            {"label": "L", "run_id": "r1", "enable_query_rewrite": True},
            0,
        )
        self.assertNotIn("QR", partial)


if __name__ == "__main__":
    unittest.main()
