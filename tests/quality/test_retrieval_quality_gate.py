import unittest

from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.summary_recall_document import SummaryRecallDocument
from src.domain.project import Project
from src.infrastructure.adapters.rag.retrieval_comparison_service import RetrievalComparisonService


def _fake_pipeline(
    *,
    rewritten_question: str,
    recalled_n: int,
    recalled_doc_ids: list[str],
    reranked_raw_assets: list[dict],
    selected_doc_ids: list[str],
    confidence: float,
) -> PipelineBuildResult:
    return PipelineBuildResult(
        rewritten_question=rewritten_question,
        recalled_summary_docs=[
            SummaryRecallDocument(page_content=str(i), metadata={}) for i in range(recalled_n)
        ],
        recalled_doc_ids=list(recalled_doc_ids),
        reranked_raw_assets=reranked_raw_assets,
        selected_doc_ids=list(selected_doc_ids),
        confidence=confidence,
    )


class _FakeRAGService:
    def __init__(self):
        self._pipelines = {
            ("invoice total", False): _fake_pipeline(
                rewritten_question="invoice total",
                recalled_n=1,
                recalled_doc_ids=["d1"],
                reranked_raw_assets=[{"doc_id": "d1"}],
                selected_doc_ids=["d1"],
                confidence=0.62,
            ),
            ("invoice total", True): _fake_pipeline(
                rewritten_question="invoice total",
                recalled_n=2,
                recalled_doc_ids=["d1", "d2"],
                reranked_raw_assets=[{"doc_id": "d1"}, {"doc_id": "d2"}],
                selected_doc_ids=["d1", "d2"],
                confidence=0.74,
            ),
            ("payment terms", False): _fake_pipeline(
                rewritten_question="payment terms",
                recalled_n=1,
                recalled_doc_ids=["d3"],
                reranked_raw_assets=[{"doc_id": "d3"}],
                selected_doc_ids=["d3"],
                confidence=0.58,
            ),
            ("payment terms", True): _fake_pipeline(
                rewritten_question="payment terms",
                recalled_n=2,
                recalled_doc_ids=["d3", "d4"],
                reranked_raw_assets=[{"doc_id": "d3"}, {"doc_id": "d4"}],
                selected_doc_ids=["d3", "d4"],
                confidence=0.69,
            ),
        }

    def inspect_pipeline(
        self,
        project,
        question,
        chat_history=None,
        *,
        enable_query_rewrite_override=None,
        enable_hybrid_retrieval_override=None,
        filters=None,
    ):
        return self._pipelines[(question, bool(enable_hybrid_retrieval_override))]


class TestRetrievalQualityGate(unittest.TestCase):
    def test_baseline_gate_hybrid_should_not_regress(self):
        project = Project(user_id="u1", project_id="p1")
        service = RetrievalComparisonService(rag_service=_FakeRAGService())
        questions = ["invoice total", "payment terms"]

        report = service.compare(
            project=project,
            questions=questions,
            enable_query_rewrite=False,
        )
        summary = report["summary"]

        # Baseline quality gates: if retrieval behavior regresses,
        # this test should fail and block the pipeline.
        self.assertEqual(summary["total_questions"], 2)
        self.assertGreaterEqual(summary["avg_hybrid_recall_doc_ids"], 2.0)
        self.assertGreaterEqual(
            summary["avg_hybrid_recall_doc_ids"],
            summary["avg_faiss_recall_doc_ids"],
        )
        self.assertGreaterEqual(
            summary["avg_hybrid_confidence"],
            summary["avg_faiss_confidence"],
        )
        self.assertGreaterEqual(summary["hybrid_wins_on_recall_doc_ids"], 2)
        self.assertGreaterEqual(summary["hybrid_wins_on_confidence"], 2)


if __name__ == "__main__":
    unittest.main()
