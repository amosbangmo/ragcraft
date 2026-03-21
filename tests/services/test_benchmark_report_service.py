import unittest
from datetime import datetime, timezone

from src.domain.benchmark_result import BenchmarkResult, BenchmarkSummary, BenchmarkRow
from src.services.benchmark_report_service import BenchmarkReportService


class TestBenchmarkReportService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = BenchmarkReportService()

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
        art = self.svc.build_export_artifacts(
            project_id="p1",
            result=result,
            enable_query_rewrite=True,
            enable_hybrid_retrieval=False,
            generated_at=datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )
        md = art.markdown_bytes.decode("utf-8")
        self.assertIn("## Notes", md)
        self.assertIn("judge_failed", md)
        self.assertIn("pipeline_failure_rate", md)

    def test_markdown_includes_run_id_when_present(self) -> None:
        result = self._minimal_result(run_id="abc123runid")
        art = self.svc.build_export_artifacts(
            project_id="p1",
            result=result,
            enable_query_rewrite=False,
            enable_hybrid_retrieval=True,
            generated_at=datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
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
        art = self.svc.build_export_artifacts(
            project_id="p1",
            result=result,
            enable_query_rewrite=True,
            enable_hybrid_retrieval=True,
            generated_at=datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )
        md = art.markdown_bytes.decode("utf-8")
        self.assertIn("## Auto-debug suggestions", md)
        self.assertIn("Tip", md)
        self.assertIn("## Failure summary", md)
        self.assertIn("retrieval_failure", md)
        self.assertIn("judge_failure", md)


if __name__ == "__main__":
    unittest.main()
