"""Tests for :class:`~application.use_cases.retrieval.compare_retrieval_modes.CompareRetrievalModesUseCase`."""

import unittest

from application.use_cases.retrieval.compare_retrieval_modes import CompareRetrievalModesUseCase
from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.rag.summary_recall_document import SummaryRecallDocument


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


class _FakeInspectRagPipelineUseCase:
    """Mimics :class:`~application.use_cases.chat.inspect_rag_pipeline.InspectRagPipelineUseCase`."""

    def __init__(self, pipelines: dict) -> None:
        self._pipelines = pipelines

    def execute(
        self,
        project,
        question,
        chat_history=None,
        *,
        filters=None,
        retrieval_overrides=None,
        enable_query_rewrite_override=None,
        enable_hybrid_retrieval_override=None,
    ):
        return self._pipelines.get((question, bool(enable_hybrid_retrieval_override)))


class _StubResolveProject:
    def __init__(self, project: Project) -> None:
        self._project = project

    def execute(self, user_id: str, project_id: str) -> Project:
        return self._project


class TestCompareRetrievalModesUseCase(unittest.TestCase):
    def setUp(self):
        self.project = Project(user_id="u1", project_id="p1")

    def test_compare_builds_summary_and_rows(self):
        pipelines = {
            ("q1", False): _fake_pipeline(
                rewritten_question="q1",
                recalled_n=1,
                recalled_doc_ids=["d1"],
                reranked_raw_assets=[{"doc_id": "d1"}],
                selected_doc_ids=["d1"],
                confidence=0.5,
            ),
            ("q1", True): _fake_pipeline(
                rewritten_question="q1",
                recalled_n=2,
                recalled_doc_ids=["d1", "d2"],
                reranked_raw_assets=[{"doc_id": "d1"}, {"doc_id": "d2"}],
                selected_doc_ids=["d1", "d2"],
                confidence=0.7,
            ),
        }
        use_case = CompareRetrievalModesUseCase(
            resolve_project=_StubResolveProject(self.project),
            inspect_pipeline=_FakeInspectRagPipelineUseCase(pipelines),
        )

        report = use_case.execute(
            user_id="u1",
            project_id="p1",
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
        use_case = CompareRetrievalModesUseCase(
            resolve_project=_StubResolveProject(self.project),
            inspect_pipeline=_FakeInspectRagPipelineUseCase({}),
        )

        report = use_case.execute(
            user_id="u1",
            project_id="p1",
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
