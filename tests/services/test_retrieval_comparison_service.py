import sys
import types
import unittest

from src.domain.project import Project

if "src.services.rag_service" not in sys.modules:
    rag_module = types.ModuleType("src.services.rag_service")

    class RAGService:
        pass

    rag_module.RAGService = RAGService
    sys.modules["src.services.rag_service"] = rag_module

from src.services.retrieval_comparison_service import RetrievalComparisonService


class _FakeRAGService:
    def __init__(self, pipelines):
        self.pipelines = pipelines

    def inspect_pipeline(
        self,
        project,
        question,
        chat_history=None,
        *,
        enable_query_rewrite_override=None,
        enable_hybrid_retrieval_override=None,
    ):
        return self.pipelines.get((question, bool(enable_hybrid_retrieval_override)))


class TestRetrievalComparisonService(unittest.TestCase):
    def setUp(self):
        self.project = Project(user_id="u1", project_id="p1")

    def test_compare_builds_summary_and_rows(self):
        pipelines = {
            ("q1", False): {
                "rewritten_question": "q1",
                "recalled_summary_docs": [1],
                "recalled_doc_ids": ["d1"],
                "reranked_raw_assets": [{"doc_id": "d1"}],
                "selected_doc_ids": ["d1"],
                "confidence": 0.5,
            },
            ("q1", True): {
                "rewritten_question": "q1",
                "recalled_summary_docs": [1, 2],
                "recalled_doc_ids": ["d1", "d2"],
                "reranked_raw_assets": [{"doc_id": "d1"}, {"doc_id": "d2"}],
                "selected_doc_ids": ["d1", "d2"],
                "confidence": 0.7,
            },
        }
        service = RetrievalComparisonService(rag_service=_FakeRAGService(pipelines))

        report = service.compare(
            project=self.project,
            questions=[" q1 ", "   "],  # blank input must be ignored
            enable_query_rewrite=False,
        )

        self.assertEqual(report["questions"], ["q1"])
        self.assertEqual(len(report["rows"]), 1)
        row = report["rows"][0]
        self.assertEqual(row["faiss_recall_doc_ids"], 1)
        self.assertEqual(row["hybrid_recall_doc_ids"], 2)
        self.assertEqual(row["hybrid_only_doc_ids"], 1)

        summary = report["summary"]
        self.assertEqual(summary["total_questions"], 1)
        self.assertEqual(summary["hybrid_wins_on_recall_doc_ids"], 1)
        self.assertEqual(summary["hybrid_wins_on_confidence"], 1)

    def test_compare_handles_missing_pipelines(self):
        service = RetrievalComparisonService(rag_service=_FakeRAGService({}))

        report = service.compare(
            project=self.project,
            questions=["q-missing"],
            enable_query_rewrite=False,
        )

        self.assertEqual(len(report["rows"]), 1)
        row = report["rows"][0]
        self.assertFalse(row["faiss_has_pipeline"])
        self.assertFalse(row["hybrid_has_pipeline"])
        self.assertEqual(row["faiss_recall_doc_ids"], 0)
        self.assertEqual(row["hybrid_recall_doc_ids"], 0)
        self.assertEqual(row["faiss_confidence"], 0.0)
        self.assertEqual(row["hybrid_confidence"], 0.0)

        summary = report["summary"]
        self.assertEqual(summary["total_questions"], 1)
        self.assertEqual(summary["hybrid_wins_on_recall_doc_ids"], 0)
        self.assertEqual(summary["hybrid_wins_on_confidence"], 0)


if __name__ == "__main__":
    unittest.main()
