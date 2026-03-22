import unittest

from src.domain.llm_judge_result import LLMJudgeResult
from src.domain.qa_dataset_entry import QADatasetEntry
from src.composition.evaluation_wiring import build_evaluation_service


class _StubJudge:
    def __init__(self, result: LLMJudgeResult) -> None:
        self._result = result

    def evaluate(self, **_kwargs) -> LLMJudgeResult:
        return self._result


class _StubSemanticSimilarity:
    def compute_similarity(self, answer: str, expected_answer: str) -> float:
        return 1.0 if (answer or "").strip() and (expected_answer or "").strip() else 0.0


class TestEvaluationServiceCitationMetrics(unittest.TestCase):
    def test_citation_overlap_when_answer_cites_expected_source(self) -> None:
        entry = QADatasetEntry(
            id=1,
            user_id="u",
            project_id="p",
            question="q?",
            expected_answer=None,
            expected_doc_ids=["doc-a"],
            expected_sources=[],
        )

        def runner(_e: QADatasetEntry):
            return {
                "pipeline": {
                    "selected_doc_ids": ["doc-a"],
                    "prompt_sources": [
                        {"source_number": 1, "doc_id": "doc-a", "source_file": "a.pdf"},
                    ],
                    "confidence": 0.5,
                    "retrieval_mode": "faiss",
                    "query_rewrite_enabled": False,
                    "hybrid_retrieval_enabled": False,
                    "raw_context": "ctx",
                },
                "answer": "Confirmed per [Source 1].",
                "latency_ms": 1.0,
            }

        judge = LLMJudgeResult(
            groundedness_score=1.0,
            citation_faithfulness_score=1.0,
            answer_relevance_score=1.0,
            hallucination_score=1.0,
            has_hallucination=False,
            reason=None,
        )
        result = build_evaluation_service(llm_judge_service=_StubJudge(judge)).evaluate_gold_qa_dataset(
            entries=[entry],
            pipeline_runner=runner,
        )
        row = result.rows[0].data
        self.assertEqual(row.get("citation_doc_ids_count"), 1)
        self.assertEqual(row.get("citation_doc_id_overlap_count"), 1)
        self.assertEqual(row.get("citation_doc_id_recall"), 1.0)
        self.assertEqual(row.get("citation_doc_id_hit_rate"), 1.0)
        self.assertEqual(row.get("citation_faithfulness_score"), 1.0)
        self.assertIn("avg_citation_doc_id_recall", result.summary.data)

    def test_citation_empty_when_answer_has_no_source_labels(self) -> None:
        entry = QADatasetEntry(
            id=1,
            user_id="u",
            project_id="p",
            question="q?",
            expected_answer="text",
            expected_doc_ids=["doc-a"],
            expected_sources=[],
        )

        def runner(_e: QADatasetEntry):
            return {
                "pipeline": {
                    "selected_doc_ids": ["doc-a"],
                    "prompt_sources": [
                        {"source_number": 1, "doc_id": "doc-a", "source_file": "a.pdf"},
                    ],
                    "confidence": 0.5,
                    "retrieval_mode": "faiss",
                    "query_rewrite_enabled": False,
                    "hybrid_retrieval_enabled": False,
                    "raw_context": "ctx",
                },
                "answer": "No bracket citations here.",
                "latency_ms": 1.0,
            }

        judge = LLMJudgeResult(
            groundedness_score=1.0,
            citation_faithfulness_score=1.0,
            answer_relevance_score=1.0,
            hallucination_score=1.0,
            has_hallucination=False,
            reason=None,
        )
        result = build_evaluation_service(
            llm_judge_service=_StubJudge(judge),
            semantic_similarity_service=_StubSemanticSimilarity(),
        ).evaluate_gold_qa_dataset(
            entries=[entry],
            pipeline_runner=runner,
        )
        row = result.rows[0].data
        self.assertEqual(row.get("citation_doc_ids_count"), 0)
        self.assertEqual(row.get("citation_doc_id_recall"), 0.0)
        self.assertEqual(row.get("citation_doc_id_hit_rate"), 0.0)
        self.assertEqual(row.get("prompt_doc_id_recall"), 1.0)
        self.assertEqual(row.get("hit_at_k"), 1.0)
        self.assertEqual(row.get("prompt_doc_id_hit_rate"), 1.0)


if __name__ == "__main__":
    unittest.main()
