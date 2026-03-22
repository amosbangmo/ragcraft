import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.domain.ingestion_diagnostics import IngestionDiagnostics
from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.domain.summary_recall_document import SummaryRecallDocument

# Populated in setUpModule; cleared in tearDownModule so stubbed packages do not
# leak into other test modules (which may be collected / run in any order).
_STUBBED_MODULE_NAMES: list[str] = []
_MODULES_TO_RELOAD_AFTER_SMOKE: tuple[str, ...] = (
    "src.frontend_gateway.in_process",
    "src.frontend_gateway.streamlit_backend_factory",
    "src.infrastructure.adapters.qa_dataset.qa_dataset_generation_service",
    "src.infrastructure.adapters.qa_dataset.qa_dataset_service",
    "src.infrastructure.persistence.sqlite.qa_dataset_repository",
)

_build_streamlit_container = None  # type: ignore[misc, assignment]
_InProcessBackendClient = None  # type: ignore[misc, assignment]


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
    global _build_streamlit_container, _InProcessBackendClient

    _install_module(
        "src.infrastructure.persistence.db",
        init_app_db=lambda: None,
        get_connection=_stub_get_connection,
    )
    _install_module("src.auth.auth_service", AuthService=_DummyService)
    _install_module("src.infrastructure.adapters.document.ingestion_service", IngestionService=_DummyService)
    _install_module("src.infrastructure.adapters.rag.vectorstore_service", VectorStoreService=_DummyService)
    _install_module("src.infrastructure.adapters.evaluation.evaluation_service", EvaluationService=_DummyService)
    _install_module(
        "src.infrastructure.adapters.evaluation.llm_judge_service",
        LLMJudgeService=_DummyService,
        JUDGE_FAILURE_REASON="judge_failure",
    )
    _install_module("src.frontend_gateway.streamlit_chat_transcript", ChatService=_DummyService)
    _install_module("src.infrastructure.adapters.rag.docstore_service", DocStoreService=_DummyService)
    _install_module("src.infrastructure.adapters.rag.reranking_service", RerankingService=_DummyService)

    from src.frontend_gateway.in_process import InProcessBackendClient as _IPC
    from src.frontend_gateway.streamlit_backend_factory import (
        build_streamlit_backend_application_container as _build,
    )

    _build_streamlit_container = _build
    _InProcessBackendClient = _IPC


def tearDownModule():
    global _build_streamlit_container, _InProcessBackendClient

    _build_streamlit_container = None
    _InProcessBackendClient = None
    for name in _MODULES_TO_RELOAD_AFTER_SMOKE:
        sys.modules.pop(name, None)
    for name in _STUBBED_MODULE_NAMES:
        sys.modules.pop(name, None)
    _STUBBED_MODULE_NAMES.clear()


class TestSmokeUploadIngestAsk(unittest.TestCase):
    def test_upload_to_ask_flow_returns_prompt_sources(self):
        assert _build_streamlit_container is not None
        assert _InProcessBackendClient is not None

        container = _build_streamlit_container()
        backend = container.backend
        client = _InProcessBackendClient(container)

        user_id = "u1"
        project_id = "p1"
        uploaded_file = SimpleNamespace(name="sample.pdf")
        project = Project(user_id=user_id, project_id=project_id)

        backend.project_service = MagicMock()
        backend.ingestion_service = MagicMock()
        backend.vectorstore_service = MagicMock()
        backend.docstore_service = MagicMock()
        client.invalidate_project_chain = MagicMock()  # type: ignore[method-assign]

        for _uc_key in (
            "ingestion_ingest_uploaded_file_use_case",
            "ingestion_reindex_document_use_case",
            "ingestion_delete_document_use_case",
        ):
            container.__dict__.pop(_uc_key, None)

        backend.project_service.get_project.return_value = project
        backend.docstore_service.get_doc_ids_for_source_file.return_value = []

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
        backend.ingestion_service.ingest_uploaded_file.return_value = (
            summary_documents,
            raw_assets,
            IngestionDiagnostics(),
        )
        backend.vectorstore_service.index_documents.return_value = (MagicMock(), 0.0)

        response = RAGResponse(
            question="What is in the document?",
            answer="The document contains a summary.",
            prompt_sources=[{"source_number": 1, "doc_id": "doc-1"}],
            raw_assets=raw_assets,
            confidence=0.9,
        )
        ask_uc = MagicMock()
        ask_uc.execute.return_value = response
        container.__dict__["chat_rag_use_cases"] = SimpleNamespace(
            ask_question=ask_uc,
            build_rag_pipeline=MagicMock(),
            inspect_rag_pipeline=MagicMock(),
            preview_summary_recall=MagicMock(),
            generate_answer_from_pipeline=MagicMock(),
        )

        ingest_result = client.ingest_uploaded_file(user_id, project_id, uploaded_file)
        ask_result = client.ask_question(
            user_id=user_id,
            project_id=project_id,
            question="What is in the document?",
            chat_history=[],
        )

        self.assertEqual(ingest_result.raw_assets, raw_assets)
        backend.docstore_service.upsert_asset.assert_called_once_with(**raw_assets[0])
        expected_index_chunks = [
            SummaryRecallDocument(page_content="summary", metadata={}),
        ]
        backend.vectorstore_service.index_documents.assert_called_once_with(project, expected_index_chunks)
        self.assertIsNotNone(ask_result)
        self.assertTrue(ask_result.prompt_sources)
        self.assertEqual(ask_result.prompt_sources[0]["doc_id"], "doc-1")


if __name__ == "__main__":
    unittest.main()
