import unittest

from src.domain.qa_dataset_entry import QADatasetEntry
from src.services.evaluation_service import EvaluationService

from tests.quality.benchmark_regression_checks import (
    BenchmarkRegressionThresholds,
    assert_benchmark_meets_thresholds,
    collect_benchmark_regression_violations,
)


class StubGroundednessService:
    def __init__(self, score: float) -> None:
        self._score = score

    def compute_groundedness(self, *, question: str, answer: str, raw_context: str) -> float:
        return self._score


def _good_pipeline_for(entry: QADatasetEntry) -> dict:
    doc_ids = list(entry.expected_doc_ids or [])
    sources = list(entry.expected_sources or [])
    refs = []
    for doc_id, src in zip(doc_ids, sources):
        refs.append({"doc_id": doc_id, "source_file": src})
    if not refs and doc_ids:
        refs = [{"doc_id": doc_ids[0], "source_file": sources[0] if sources else "s.pdf"}]
    return {
        "selected_doc_ids": doc_ids or ["d1"],
        "source_references": refs
        or [{"doc_id": "d1", "source_file": sources[0] if sources else "s.pdf"}],
        "confidence": 0.9,
        "retrieval_mode": "hybrid",
        "query_rewrite_enabled": False,
        "hybrid_retrieval_enabled": True,
        "raw_context": "Synthetic context for groundedness stub tests.",
    }


class TestBenchmarkRegressionFlow(unittest.TestCase):
    def test_evaluation_service_output_passes_sane_thresholds(self):
        entries = [
            QADatasetEntry(
                id=1,
                user_id="u1",
                project_id="p1",
                question="What is the total?",
                expected_answer="one hundred",
                expected_doc_ids=["doc-a"],
                expected_sources=["invoice.pdf"],
            ),
            QADatasetEntry(
                id=2,
                user_id="u1",
                project_id="p1",
                question="Due date?",
                expected_answer="next Friday",
                expected_doc_ids=["doc-b"],
                expected_sources=["contract.pdf"],
            ),
        ]

        def runner(entry: QADatasetEntry):
            return {
                "pipeline": _good_pipeline_for(entry),
                "answer": entry.expected_answer or "",
                "latency_ms": 10.0,
            }

        result = EvaluationService(
            groundedness_service=StubGroundednessService(1.0),
        ).evaluate_gold_qa_dataset(
            entries=entries,
            pipeline_runner=runner,
        )

        thresholds = BenchmarkRegressionThresholds(
            min_successful_queries=2,
            min_avg_doc_id_recall=0.99,
            min_avg_answer_f1=0.99,
            min_avg_citation_source_f1=0.99,
            min_avg_groundedness=0.99,
        )
        assert_benchmark_meets_thresholds(result, thresholds)

    def test_evaluation_service_regression_detected_when_runner_degrades(self):
        entries = [
            QADatasetEntry(
                id=1,
                user_id="u1",
                project_id="p1",
                question="q1",
                expected_answer="a1",
                expected_doc_ids=["expected-x"],
                expected_sources=["s1.pdf"],
            ),
        ]

        def broken_runner(_entry: QADatasetEntry):
            return {
                "pipeline": {
                    "selected_doc_ids": ["wrong-id"],
                    "source_references": [{"doc_id": "wrong-id", "source_file": "other.pdf"}],
                    "confidence": 0.1,
                    "retrieval_mode": "faiss",
                    "query_rewrite_enabled": False,
                    "hybrid_retrieval_enabled": False,
                    "raw_context": "Unrelated context.",
                },
                "answer": "unrelated answer tokens",
                "latency_ms": 5.0,
            }

        result = EvaluationService(
            groundedness_service=StubGroundednessService(0.0),
        ).evaluate_gold_qa_dataset(
            entries=entries,
            pipeline_runner=broken_runner,
        )

        thresholds = BenchmarkRegressionThresholds(
            min_successful_queries=1,
            min_avg_doc_id_recall=0.5,
            min_avg_answer_f1=0.5,
            min_avg_citation_source_f1=0.5,
            min_avg_groundedness=0.5,
        )
        violations = collect_benchmark_regression_violations(result, thresholds)
        self.assertTrue(violations)
