import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from components.shared import evaluation_dashboard as ed


def _expander_cm():
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=None)
    m.__exit__ = MagicMock(return_value=False)
    return m


class TestEvaluationDashboardRenderHelpers(unittest.TestCase):
    def _mock_streamlit(self, mock_st) -> None:
        mock_st.expander.side_effect = lambda *a, **k: _expander_cm()

        def _cols(*args, **kwargs):
            n = int(args[0]) if args and isinstance(args[0], int) else 3
            return [MagicMock() for _ in range(n)]

        mock_st.columns.side_effect = _cols

    @patch("components.shared.evaluation_dashboard.st")
    def test_render_correlation_none_and_unavailable(self, mock_st) -> None:
        self._mock_streamlit(mock_st)
        ed._render_correlation_analysis(None, [])
        ed._render_correlation_analysis({"available": False, "reason": "too few"}, [])

    @patch("components.shared.evaluation_dashboard.st")
    def test_render_correlation_full_matrix_and_scatter(self, mock_st) -> None:
        self._mock_streamlit(mock_st)
        correlations = {
            "available": True,
            "strong_threshold": 0.6,
            "metrics_used": ["confidence", "answer_f1"],
            "matrix": {
                "confidence": {"answer_f1": 0.8},
            },
            "highlights": {
                "strong_positive": [{"metric_a": "confidence", "metric_b": "answer_f1", "r": 0.8}],
                "strong_negative": [],
            },
            "sample_size": 5,
        }
        rows = [
            {"confidence": 0.5, "answer_f1": 0.6},
            {"confidence": 0.6, "answer_f1": 0.7},
        ]
        ed._render_correlation_analysis(correlations, rows)

    @patch("components.shared.evaluation_dashboard.st")
    def test_render_correlation_no_strong_pairs(self, mock_st) -> None:
        self._mock_streamlit(mock_st)
        correlations = {
            "available": True,
            "strong_threshold": 0.99,
            "metrics_used": ["a", "b"],
            "matrix": {"a": {"b": 0.1}},
            "highlights": {"strong_positive": [], "strong_negative": []},
            "sample_size": 2,
        }
        ed._render_correlation_analysis(correlations, [{"a": 1, "b": 2}])

    @patch("components.shared.evaluation_dashboard.st")
    def test_render_failure_analysis_paths(self, mock_st) -> None:
        self._mock_streamlit(mock_st)
        ed._render_failure_analysis(None, [])
        ed._render_failure_analysis({}, [{"entry_id": 1}])
        payload = {
            "failed_row_count": 2,
            "critical_count": 1,
            "counts": {"retrieval_failure": 2, "bad": "x"},
            "top_failure_types": [{"type": "retrieval_failure", "count": 2}],
            "examples": {
                "retrieval_failure": [
                    {
                        "entry_id": 9,
                        "question": "q?",
                        "failure_critical": True,
                        "failure_labels": ["judge_failure"],
                        "answer_preview": "prev",
                        "recall_at_k": 0.0,
                        "answer_f1": 0.1,
                        "groundedness_score": 0.2,
                        "hallucination_score": 0.3,
                        "answer_relevance_score": 0.4,
                        "confidence": 0.9,
                    }
                ]
            },
        }
        ed._render_failure_analysis(payload, [{"entry_id": 1}])

    @patch("components.shared.evaluation_dashboard.st")
    def test_render_failure_no_counts_success(self, mock_st) -> None:
        self._mock_streamlit(mock_st)
        ed._render_failure_analysis(
            {"failed_row_count": 0, "critical_count": 0, "counts": {}},
            [{"entry_id": 1}],
        )

    @patch("components.shared.evaluation_dashboard.st")
    def test_histogram_and_overview_charts(self, mock_st) -> None:
        self._mock_streamlit(mock_st)
        ed._histogram_bar_chart("L", None)
        ed._histogram_bar_chart("L", pd.Series([float("nan")]))
        ed._histogram_bar_chart("L", pd.Series([0.1, 0.2, 0.3]))
        ed.render_overview_insight_charts([])
        ed.render_overview_insight_charts([{"groundedness_score": 0.5, "recall_at_k": 0.25}])


if __name__ == "__main__":
    unittest.main()
