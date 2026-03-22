import unittest

from src.domain import benchmark_metric_taxonomy as bmt
from src.infrastructure.adapters.evaluation.benchmark_comparison_service import (
    BenchmarkComparisonService,
    LOWER_IS_BETTER_METRICS,
)
from src.ui import metric_help


class TestBenchmarkMetricTaxonomy(unittest.TestCase):
    def test_every_metric_help_key_has_spec(self) -> None:
        missing = [k for k in metric_help.METRIC_HELP if k not in bmt.METRIC_SPECS]
        self.assertEqual(
            missing,
            [],
            f"Add entries to METRIC_SPECS for: {missing}",
        )

    def test_correlation_row_keys_have_specs(self) -> None:
        missing = [rk for _, rk in bmt.CORRELATION_METRIC_KEYS if rk not in bmt.METRIC_SPECS]
        self.assertEqual(missing, [])

    def test_lower_is_better_includes_historical_summary_keys(self) -> None:
        historical = frozenset(
            {"avg_latency_ms", "pipeline_failure_rate", "hallucination_rate"}
        )
        self.assertTrue(historical <= bmt.LOWER_IS_BETTER_METRIC_KEYS)
        self.assertEqual(LOWER_IS_BETTER_METRICS, bmt.LOWER_IS_BETTER_METRIC_KEYS)

    def test_lower_is_better_matches_spec_direction(self) -> None:
        for key in bmt.LOWER_IS_BETTER_METRIC_KEYS:
            spec = bmt.METRIC_SPECS[key]
            self.assertEqual(
                spec.direction,
                bmt.MetricDirection.LOWER_BETTER,
                key,
            )

    def test_critical_regression_keys_unchanged(self) -> None:
        self.assertEqual(
            bmt.CRITICAL_REGRESSION_METRIC_KEYS,
            frozenset({"avg_answer_f1", "avg_groundedness_score", "avg_answer_correctness"}),
        )

    def test_is_lower_better_unknown_defaults_false(self) -> None:
        self.assertFalse(bmt.is_lower_better("not_a_real_metric_key"))

    def test_markdown_family_guide_non_empty(self) -> None:
        lines = bmt.markdown_family_guide_lines()
        self.assertTrue(any("retrieval_ranked_docs" in ln for ln in lines))
        self.assertTrue(any("LOWER_IS_BETTER_METRIC_KEYS" in ln for ln in lines))

    def test_compare_service_uses_taxonomy_lower_is_better(self) -> None:
        a = {k: 1.0 for k in bmt.LOWER_IS_BETTER_METRIC_KEYS}
        b = {k: 0.5 for k in bmt.LOWER_IS_BETTER_METRIC_KEYS}
        rows = BenchmarkComparisonService().compare(a, b)
        by_m = {r["metric"]: r["direction"] for r in rows}
        for k in bmt.LOWER_IS_BETTER_METRIC_KEYS:
            self.assertEqual(by_m.get(k), "improved", k)


if __name__ == "__main__":
    unittest.main()
