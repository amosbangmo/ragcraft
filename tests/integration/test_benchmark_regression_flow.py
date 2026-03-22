import unittest

from src.domain.llm_judge_result import LLMJudgeResult
from src.domain.qa_dataset_entry import QADatasetEntry
from src.composition.evaluation_wiring import build_evaluation_service

from tests.quality.benchmark_regression_checks import (
    BenchmarkRegressionThresholds,
    assert_benchmark_meets_thresholds,
    collect_benchmark_regression_violations,
)


class StubLLMJudgeService:
    def __init__(self, result: LLMJudgeResult) -> None:
        self._result = result

    def evaluate(self, **_kwargs) -> LLMJudgeResult:
        return self._result


class StubSemanticSimilarityService:
    def compute_similarity(self, answer: str, expected_answer: str) -> float:
        return 1.0 if (answer or "").strip() and (expected_answer or "").strip() else 0.0


def _good_pipeline_for(entry: QADatasetEntry) -> dict:
    doc_ids = list(entry.expected_doc_ids or [])
    sources = list(entry.expected_sources or [])
    refs = []
    for doc_id, src in zip(doc_ids, sources):
        refs.append({"doc_id": doc_id, "source_file": src, "content_type": "text"})
    if not refs and doc_ids:
        refs = [{"doc_id": doc_ids[0], "source_file": sources[0] if sources else "s.pdf", "content_type": "text"}]
    base_doc = doc_ids[0] if doc_ids else "d1"
    base_src = sources[0] if sources else "s.pdf"
    prompt_assets = [
        {"doc_id": base_doc, "source_file": base_src, "content_type": "text"},
        {"doc_id": base_doc, "source_file": base_src, "content_type": "table"},
    ]
    return {
        "selected_doc_ids": doc_ids or ["d1"],
        "prompt_sources": refs
        or [{"doc_id": "d1", "source_file": sources[0] if sources else "s.pdf", "content_type": "text"}],
        "prompt_context_assets": prompt_assets,
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

        judge = LLMJudgeResult(
            groundedness_score=1.0,
            citation_faithfulness_score=1.0,
            answer_relevance_score=1.0,
            hallucination_score=1.0,
            has_hallucination=False,
            answer_correctness_score=1.0,
            reason=None,
        )
        result = build_evaluation_service(
            llm_judge_service=StubLLMJudgeService(judge),
            semantic_similarity_service=StubSemanticSimilarityService(),
        ).evaluate_gold_qa_dataset(
            entries=entries,
            pipeline_runner=runner,
        )

        thresholds = BenchmarkRegressionThresholds(
            min_successful_queries=2,
            min_avg_recall_at_k=0.99,
            min_avg_answer_f1=0.99,
            min_avg_prompt_doc_id_f1=0.99,
            min_avg_groundedness_score=0.99,
            min_avg_answer_relevance_score=0.99,
        )
        assert_benchmark_meets_thresholds(result, thresholds)
        mm = result.multimodal_metrics
        self.assertIsNotNone(mm)
        self.assertTrue(mm.get("has_multimodal_assets"))
        self.assertEqual(mm.get("table_usage_rate"), 1.0)

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
                    "prompt_sources": [{"doc_id": "wrong-id", "source_file": "other.pdf"}],
                    "confidence": 0.1,
                    "retrieval_mode": "faiss",
                    "query_rewrite_enabled": False,
                    "hybrid_retrieval_enabled": False,
                    "raw_context": "Unrelated context.",
                },
                "answer": "unrelated answer tokens",
                "latency_ms": 5.0,
            }

        judge = LLMJudgeResult(
            groundedness_score=0.0,
            citation_faithfulness_score=0.0,
            answer_relevance_score=0.0,
            hallucination_score=0.0,
            has_hallucination=True,
            answer_correctness_score=0.0,
            reason=None,
        )
        result = build_evaluation_service(
            llm_judge_service=StubLLMJudgeService(judge),
            semantic_similarity_service=StubSemanticSimilarityService(),
        ).evaluate_gold_qa_dataset(
            entries=entries,
            pipeline_runner=broken_runner,
        )

        thresholds = BenchmarkRegressionThresholds(
            min_successful_queries=1,
            min_avg_recall_at_k=0.5,
            min_avg_answer_f1=0.5,
            min_avg_prompt_doc_id_f1=0.5,
            min_avg_groundedness_score=0.5,
            min_avg_answer_relevance_score=0.5,
        )
        violations = collect_benchmark_regression_violations(result, thresholds)
        self.assertTrue(violations)
