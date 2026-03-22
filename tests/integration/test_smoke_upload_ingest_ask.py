import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.domain.ingestion_diagnostics import IngestionDiagnostics
from src.domain.project import Project
from src.domain.rag_response import RAGResponse

# Populated in setUpModule; cleared in tearDownModule so stubbed packages do not
# leak into other test modules (which may be collected / run in any order).
_STUBBED_MODULE_NAMES: list[str] = []
_MODULES_TO_RELOAD_AFTER_SMOKE: tuple[str, ...] = (
    "src.app.ragcraft_app",
    "src.services.qa_dataset_generation_service",
    "src.services.qa_dataset_service",
    "src.infrastructure.persistence.sqlite.qa_dataset_repository",
)

RAGCraftApp = None  # type: ignore[misc, assignment]


def _install_module(module_name: str, **attributes):
    module = types.ModuleType(module_name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[module_name] = module
    _STUBBED_MODULE_NAMES.append(module_name)


class _DummyService:
    def __init__(self, *args, **kwargs):
        pass


def _stub_get_connection():
    conn = MagicMock(name="sqlite_conn")
    conn.execute = MagicMock(return_value=MagicMock())
    conn.commit = MagicMock()
    conn.rollback = MagicMock()
    conn.close = MagicMock()
    return conn


def setUpModule():
    global RAGCraftApp

    _install_module(
        "src.infrastructure.persistence.db",
        init_app_db=lambda: None,
        get_connection=_stub_get_connection,
    )
    _install_module("src.auth.auth_service", AuthService=_DummyService)
    _install_module("src.services.ingestion_service", IngestionService=_DummyService)
    _install_module("src.services.vectorstore_service", VectorStoreService=_DummyService)
    _install_module("src.services.evaluation_service", EvaluationService=_DummyService)
    _install_module(
        "src.services.llm_judge_service",
        LLMJudgeService=_DummyService,
        JUDGE_FAILURE_REASON="judge_failure",
    )
    _install_module("src.services.chat_service", ChatService=_DummyService)
    _install_module("src.services.rag_service", RAGService=_DummyService)
    _install_module("src.services.docstore_service", DocStoreService=_DummyService)
    _install_module("src.services.reranking_service", RerankingService=_DummyService)
    _install_module(
        "src.services.retrieval_comparison_service",
        RetrievalComparisonService=_DummyService,
    )

    from src.app.ragcraft_app import RAGCraftApp as _RAGCraftApp

    RAGCraftApp = _RAGCraftApp


def tearDownModule():
    global RAGCraftApp

    RAGCraftApp = None
    for name in _MODULES_TO_RELOAD_AFTER_SMOKE:
        sys.modules.pop(name, None)
    for name in _STUBBED_MODULE_NAMES:
        sys.modules.pop(name, None)
    _STUBBED_MODULE_NAMES.clear()


class TestSmokeUploadIngestAsk(unittest.TestCase):
    def test_upload_to_ask_flow_returns_prompt_sources(self):
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
        app._backend._rag_service = MagicMock()
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
        app.ingestion_service.ingest_uploaded_file.return_value = (
            summary_documents,
            raw_assets,
            IngestionDiagnostics(),
        )
        app.vectorstore_service.index_documents.return_value = (MagicMock(), 0.0)

        response = RAGResponse(
            question="What is in the document?",
            answer="The document contains a summary.",
            prompt_sources=[{"source_number": 1, "doc_id": "doc-1"}],
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
        app.docstore_service.upsert_asset.assert_called_once_with(**raw_assets[0])
        app.vectorstore_service.index_documents.assert_called_once_with(project, summary_documents)
        self.assertIsNotNone(ask_result)
        self.assertTrue(ask_result.prompt_sources)
        self.assertEqual(ask_result.prompt_sources[0]["doc_id"], "doc-1")


if __name__ == "__main__":
    unittest.main()
