import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from application.dto.ingestion import IngestUploadedFileCommand
from domain.common.ingestion_diagnostics import IngestionDiagnostics
from domain.projects.buffered_document_upload import BufferedDocumentUpload
from domain.projects.project import Project
from domain.rag.rag_response import RAGResponse
from domain.rag.summary_recall_document import SummaryRecallDocument

_STUBBED_MODULE_NAMES: list[str] = []
_MODULES_TO_RELOAD_AFTER_SMOKE: tuple[str, ...] = (
    "services.factories.chat_service_factory",
    "services.factories",
    "infrastructure.evaluation.qa_dataset_generation_service",
    "infrastructure.evaluation.qa_dataset_service",
    "infrastructure.persistence.sqlite.qa_dataset_repository",
)

_build_streamlit_container = None  # type: ignore[misc, assignment]


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
    global _build_streamlit_container

    _install_module(
        "infrastructure.persistence.db",
        init_app_db=lambda: None,
        get_connection=_stub_get_connection,
    )
    _install_module("infrastructure.auth.auth_service", AuthService=_DummyService)
    _install_module("infrastructure.rag.ingestion_service", IngestionService=_DummyService)
    _install_module("infrastructure.rag.vectorstore_service", VectorStoreService=_DummyService)
    _install_module("infrastructure.evaluation.evaluation_service", EvaluationService=_DummyService)
    _install_module(
        "infrastructure.evaluation.llm_judge_service",
        LLMJudgeService=_DummyService,
        JUDGE_FAILURE_REASON="judge_failure",
    )
    _install_module("services.streamlit_chat_transcript", StreamlitChatTranscript=_DummyService)
    _install_module("infrastructure.rag.docstore_service", DocStoreService=_DummyService)
    _install_module("infrastructure.rag.reranking_service", RerankingService=_DummyService)

    from support.backend_container import (
        build_streamlit_session_aware_backend_container_for_tests as _build,
    )

    _build_streamlit_container = _build


def tearDownModule():
    global _build_streamlit_container

    _build_streamlit_container = None
    for name in _MODULES_TO_RELOAD_AFTER_SMOKE:
        sys.modules.pop(name, None)
    for name in _STUBBED_MODULE_NAMES:
        sys.modules.pop(name, None)
    _STUBBED_MODULE_NAMES.clear()


class TestSmokeUploadIngestAsk(unittest.TestCase):
    def test_upload_to_ask_flow_returns_prompt_sources(self):
        assert _build_streamlit_container is not None

        container = _build_streamlit_container()
        backend = container.backend

        user_id = "u1"
        project_id = "p1"
        _pdf_bytes = b"%PDF-1.4 minimal"
        upload = BufferedDocumentUpload(source_filename="sample.pdf", body=_pdf_bytes)
        project = Project(user_id=user_id, project_id=project_id)

        backend.project_service = MagicMock()
        backend.ingestion_service = MagicMock()
        backend.vectorstore_service = MagicMock()
        backend.docstore_service = MagicMock()

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
                "source_file": upload.name,
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

        ingest_uc = container.ingestion_ingest_uploaded_file_use_case
        ingest_result = ingest_uc.execute(IngestUploadedFileCommand(project=project, upload=upload))
        ask_result = container.chat_ask_question_use_case.execute(
            project,
            "What is in the document?",
            [],
        )

        self.assertEqual(len(ingest_result.raw_assets), len(raw_assets))
        backend.docstore_service.upsert_asset.assert_called_once_with(**raw_assets[0])
        expected_index_chunks = [
            SummaryRecallDocument(page_content="summary", metadata={}),
        ]
        backend.vectorstore_service.index_documents.assert_called_once_with(
            project, expected_index_chunks
        )
        self.assertIsNotNone(ask_result)
        self.assertTrue(ask_result.prompt_sources)
        self.assertEqual(ask_result.prompt_sources[0]["doc_id"], "doc-1")


if __name__ == "__main__":
    unittest.main()
