import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.domain.project import Project
from src.domain.rag_response import RAGResponse


def _install_module(module_name: str, **attributes):
    module = types.ModuleType(module_name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[module_name] = module


class _DummyService:
    def __init__(self, *args, **kwargs):
        pass


# Lightweight module stubs so importing RAGCraftApp does not require
# optional runtime dependencies (LLM, FAISS, OCR stack, etc.).
_install_module("src.infrastructure.persistence.db", init_app_db=lambda: None)
_install_module("src.auth.auth_service", AuthService=_DummyService)
_install_module("src.services.ingestion_service", IngestionService=_DummyService)
_install_module("src.services.vectorstore_service", VectorStoreService=_DummyService)
_install_module("src.services.evaluation_service", EvaluationService=_DummyService)
_install_module("src.services.groundedness_service", GroundednessService=_DummyService)
_install_module(
    "src.services.citation_faithfulness_service",
    CitationFaithfulnessService=_DummyService,
)
_install_module("src.services.answer_relevance_service", AnswerRelevanceService=_DummyService)
_install_module("src.services.hallucination_service", HallucinationService=_DummyService)
_install_module("src.services.chat_service", ChatService=_DummyService)
_install_module("src.services.rag_service", RAGService=_DummyService)
_install_module("src.services.docstore_service", DocStoreService=_DummyService)
_install_module("src.services.reranking_service", RerankingService=_DummyService)
_install_module(
    "src.services.retrieval_comparison_service",
    RetrievalComparisonService=_DummyService,
)

from src.app.ragcraft_app import RAGCraftApp


class TestSmokeUploadIngestAsk(unittest.TestCase):
    def test_upload_to_ask_flow_returns_citations(self):
        app = RAGCraftApp()

        user_id = "u1"
        project_id = "p1"
        uploaded_file = SimpleNamespace(name="sample.pdf")
        project = Project(user_id=user_id, project_id=project_id)

        # Swap service instances with mocks to run a deterministic smoke flow.
        app.project_service = MagicMock()
        app.ingestion_service = MagicMock()
        app.vectorstore_service = MagicMock()
        app.docstore_service = MagicMock()
        app._rag_service = MagicMock()
        app.invalidate_project_chain = MagicMock()

        app.project_service.get_project.return_value = project
        app.docstore_service.get_doc_ids_for_source_file.return_value = []

        summary_documents = [SimpleNamespace(page_content="summary")]
        raw_assets = [
            {
                "doc_id": "doc-1",
                "user_id": user_id,
                "project_id": project_id,
                "source_file": uploaded_file.name,
                "content_type": "text",
                "raw_content": "raw text",
                "summary": "summary",
                "metadata": {"page_number": 1},
            }
        ]
        app.ingestion_service.ingest_uploaded_file.return_value = (summary_documents, raw_assets)

        response = RAGResponse(
            question="What is in the document?",
            answer="The document contains a summary.",
            citations=[{"source_number": 1, "doc_id": "doc-1"}],
            raw_assets=raw_assets,
            confidence=0.9,
        )
        app.rag_service.ask.return_value = response

        ingest_result = app.ingest_uploaded_file(user_id, project_id, uploaded_file)
        ask_result = app.ask_question(
            user_id=user_id,
            project_id=project_id,
            question="What is in the document?",
            chat_history=[],
        )

        self.assertEqual(ingest_result["raw_assets"], raw_assets)
        app.docstore_service.save_asset.assert_called_once_with(**raw_assets[0])
        app.vectorstore_service.index_documents.assert_called_once_with(project, summary_documents)
        self.assertIsNotNone(ask_result)
        self.assertTrue(ask_result.citations)
        self.assertEqual(ask_result.citations[0]["doc_id"], "doc-1")


if __name__ == "__main__":
    unittest.main()
