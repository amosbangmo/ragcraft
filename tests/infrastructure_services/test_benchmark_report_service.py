import json
import unittest
from datetime import datetime, timezone

from src.application.evaluation.benchmark_export_dtos import BuildBenchmarkExportCommand
from src.application.evaluation.benchmark_report_formatter import coerce_generated_at, safe_filename_segment
from src.application.use_cases.evaluation.build_benchmark_export_artifacts import (
    BuildBenchmarkExportArtifactsUseCase,
)
from src.domain.benchmark_result import BenchmarkResult, BenchmarkRow, BenchmarkSummary


class TestCoerceGeneratedAt(unittest.TestCase):
    def test_none(self) -> None:
        self.assertIsNone(coerce_generated_at(None))

    def test_empty_string(self) -> None:
        self.assertIsNone(coerce_generated_at(""))
        self.assertIsNone(coerce_generated_at("   "))

    def test_invalid_string(self) -> None:
        self.assertIsNone(coerce_generated_at("not-a-date"))

    def test_non_string_non_datetime(self) -> None:
        self.assertIsNone(coerce_generated_at(12345))

    def test_datetime_passthrough(self) -> None:
        dt = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        self.assertEqual(coerce_generated_at(dt), dt)

    def test_iso_string_z_suffix(self) -> None:
        out = coerce_generated_at("2025-01-02T03:04:05Z")
        assert out is not None
        self.assertEqual(out.tzinfo, timezone.utc)


class TestSafeFilenameSegment(unittest.TestCase):
    def test_sanitizes_and_truncates(self) -> None:
        self.assertEqual(safe_filename_segment("a/b:c"), "a_b_c")
        self.assertEqual(len(safe_filename_segment("x" * 200, max_length=10)), 10)

    def test_empty_defaults_to_project(self) -> None:
        self.assertEqual(safe_filename_segment(""), "project")
        self.assertEqual(safe_filename_segment("   "), "project")


class TestBenchmarkExportArtifactsUseCase(unittest.TestCase):
    def setUp(self) -> None:
        self.uc = BuildBenchmarkExportArtifactsUseCase()

    def _minimal_result(
        self,
        *,
        run_id: str | None = None,
        auto_debug: list[dict[str, str]] | None = None,
        failures: dict | None = None,
    ) -> BenchmarkResult:
        return BenchmarkResult(
            summary=BenchmarkSummary(data={"total_entries": 1}),
            rows=[
                BenchmarkRow(
                    entry_id=1,
                    question="Q",
                    data={"recall_at_k": 0.5, "pipeline_failed": False, "judge_failed": False},
                )
            ],
            run_id=run_id,
            auto_debug=auto_debug,
            failures=failures,
        )

    def test_markdown_includes_notes_section(self) -> None:
        result = self._minimal_result()
        art = self.uc.execute(
            BuildBenchmarkExportCommand(
                project_id="p1",
                result=result,
                enable_query_rewrite=True,
                enable_hybrid_retrieval=False,
                generated_at=datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            )
        )
        md = art.markdown_bytes.decode("utf-8")
        self.assertIn("## Notes", md)
        self.assertIn("judge_failed", md)
        self.assertIn("pipeline_failure_rate", md)
        self.assertIn("retrieval_ranked_docs", md)

    def test_build_accepts_iso_string_generated_at(self) -> None:
        result = self._minimal_result()
        art = self.uc.execute(
            BuildBenchmarkExportCommand(
                project_id="p1",
                result=result,
                enable_query_rewrite=True,
                enable_hybrid_retrieval=False,
                generated_at="2025-06-15T12:00:00+00:00",
            )
        )
        self.assertTrue(art.json_filename.endswith(".json"))
        self.assertIn("2025-06-15", art.metadata.generated_at_utc)

    def test_markdown_includes_run_id_when_present(self) -> None:
        result = self._minimal_result(run_id="abc123runid")
        art = self.uc.execute(
            BuildBenchmarkExportCommand(
                project_id="p1",
                result=result,
                enable_query_rewrite=False,
                enable_hybrid_retrieval=True,
                generated_at=datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            )
        )
        md = art.markdown_bytes.decode("utf-8")
        self.assertIn("## Run context", md)
        self.assertIn("abc123runid", md)
        self.assertEqual(art.run_id, "abc123runid")

    def test_markdown_includes_auto_debug_and_failures_when_present(self) -> None:
        result = self._minimal_result(
            auto_debug=[{"title": "Tip", "description": "Do something useful."}],
            failures={
                "counts": {"retrieval_failure": 2, "judge_failure": 1},
                "failed_row_count": 3,
                "critical_count": 0,
            },
        )
        art = self.uc.execute(
            BuildBenchmarkExportCommand(
                project_id="p1",
                result=result,
                enable_query_rewrite=True,
                enable_hybrid_retrieval=True,
                generated_at=datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            )
        )
        md = art.markdown_bytes.decode("utf-8")
        self.assertIn("## Auto-debug suggestions", md)
        self.assertIn("Tip", md)
        self.assertIn("## Failure summary", md)
        self.assertIn("retrieval_failure", md)
        self.assertIn("judge_failure", md)

    def test_json_includes_optional_sections(self) -> None:
        result = BenchmarkResult(
            summary=BenchmarkSummary(data={"total_entries": 0}),
            rows=[],
            correlations={"available": False},
            failures={"failed_row_count": 0, "counts": {}},
            multimodal_metrics={"has_multimodal_assets": False},
            auto_debug=[{"title": "T", "description": "D"}],
            run_id="run-json",
        )
        art = self.uc.execute(
            BuildBenchmarkExportCommand(
                project_id="proj",
                result=result,
                enable_query_rewrite=False,
                enable_hybrid_retrieval=False,
                generated_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            )
        )
        payload = json.loads(art.json_bytes.decode("utf-8"))
        self.assertEqual(payload["run_id"], "run-json")
        self.assertIn("correlations", payload)
        self.assertIn("failures", payload)
        self.assertIn("multimodal_metrics", payload)
        self.assertEqual(payload["auto_debug"], [{"title": "T", "description": "D"}])

    def test_csv_utf8_bom_and_headers(self) -> None:
        result = BenchmarkResult(
            summary=BenchmarkSummary(data={"total_entries": 1}),
            rows=[
                BenchmarkRow(
                    entry_id=9,
                    question="Q|x",
                    data={"recall_at_k": 0.25, "nested": [1, 2]},
                )
            ],
        )
        art = self.uc.execute(
            BuildBenchmarkExportCommand(
                project_id="p",
                result=result,
                enable_query_rewrite=True,
                enable_hybrid_retrieval=False,
                generated_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            )
        )
        raw = art.csv_bytes
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        text = raw.decode("utf-8-sig")
        lines = text.strip().split("\n")
        self.assertIn("entry_id", lines[0])
        self.assertIn("nested", lines[0])
        self.assertIn("9", lines[1])

    def test_markdown_empty_rows_placeholder(self) -> None:
        result = BenchmarkResult(
            summary=BenchmarkSummary(data={"total_entries": 0}),
            rows=[],
        )
        art = self.uc.execute(
            BuildBenchmarkExportCommand(
                project_id="p",
                result=result,
                enable_query_rewrite=False,
                enable_hybrid_retrieval=False,
                generated_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            )
        )
        md = art.markdown_bytes.decode("utf-8")
        self.assertIn("_No benchmark rows._", md)
        self.assertIn("## Summary metrics", md)

    def test_markdown_skips_blank_auto_debug_items(self) -> None:
        result = BenchmarkResult(
            summary=BenchmarkSummary(data={"total_entries": 1}),
            rows=[
                BenchmarkRow(entry_id=1, question="q", data={}),
            ],
            auto_debug=[
                {"title": "", "description": ""},
                {"title": "Keep", "description": "Yes"},
            ],
        )
        art = self.uc.execute(
            BuildBenchmarkExportCommand(
                project_id="p",
                result=result,
                enable_query_rewrite=False,
                enable_hybrid_retrieval=False,
                generated_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            )
        )
        md = art.markdown_bytes.decode("utf-8")
        self.assertIn("Keep", md)
        self.assertIn("Yes", md)


if __name__ == "__main__":
    unittest.main()
