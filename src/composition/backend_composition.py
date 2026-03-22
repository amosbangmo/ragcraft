"""
Backend service graph: persistence bootstrap and **technical** infrastructure adapters only.

Construction is **deterministic** in :func:`build_backend_composition`. Cross-cutting RAG/chat wiring
and use cases live in :mod:`src.composition.application_container` (and :mod:`src.composition.chat_rag_wiring`).

Layers (in build order):
1. SQLite app DB (:func:`~src.infrastructure.persistence.db.init_app_db`).
2. Adapters: auth, projects, ingestion, vector store, evaluation, chat session, doc store, reranking,
   QA dataset + generation, project settings repository, retrieval settings, query logging.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.infrastructure.adapters.sqlite.project_settings_repository import SqliteProjectSettingsRepository
from src.infrastructure.adapters.sqlite.user_repository import SqliteUserRepository
from src.auth.auth_service import AuthService
from src.domain.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from src.infrastructure.persistence.db import init_app_db
from src.frontend_gateway.streamlit_chat_transcript import ChatService
from src.infrastructure.adapters.rag.docstore_service import DocStoreService
from src.infrastructure.adapters.evaluation.evaluation_service import EvaluationService
from src.infrastructure.adapters.evaluation.llm_judge_service import LLMJudgeService
from src.infrastructure.adapters.workspace.project_service import ProjectService
from src.infrastructure.adapters.qa_dataset.qa_dataset_generation_service import QADatasetGenerationService
from src.infrastructure.adapters.qa_dataset.qa_dataset_service import QADatasetService
from src.infrastructure.adapters.query_logging.query_log_service import QueryLogService
from src.infrastructure.adapters.rag.reranking_service import RerankingService
from src.infrastructure.adapters.rag.retrieval_settings_service import RetrievalSettingsService

if TYPE_CHECKING:
    from src.infrastructure.adapters.document.ingestion_service import IngestionService
    from src.infrastructure.adapters.rag.vectorstore_service import VectorStoreService


@dataclass
class BackendComposition:
    """Immutable graph of technical dependencies for one process (API or Streamlit)."""

    query_log_service: QueryLogService
    auth_service: AuthService
    project_service: ProjectService
    ingestion_service: IngestionService
    vectorstore_service: VectorStoreService
    evaluation_service: EvaluationService
    chat_service: ChatService
    docstore_service: DocStoreService
    reranking_service: RerankingService
    qa_dataset_service: QADatasetService
    qa_dataset_generation_service: QADatasetGenerationService
    project_settings_repository: ProjectSettingsRepositoryPort
    retrieval_settings_service: RetrievalSettingsService


def build_backend_composition() -> BackendComposition:
    """Assemble technical adapters only (no application use cases)."""
    from src.infrastructure.adapters.document.ingestion_service import IngestionService
    from src.infrastructure.adapters.rag.vectorstore_service import VectorStoreService

    init_app_db()

    query_log_service = QueryLogService()
    project_service = ProjectService()
    docstore_service = DocStoreService()
    project_settings_repository = SqliteProjectSettingsRepository()
    retrieval_settings_service = RetrievalSettingsService(
        project_settings_repository=project_settings_repository,
    )

    return BackendComposition(
        query_log_service=query_log_service,
        auth_service=AuthService(user_repository=SqliteUserRepository()),
        project_service=project_service,
        ingestion_service=IngestionService(),
        vectorstore_service=VectorStoreService(),
        evaluation_service=EvaluationService(llm_judge_service=LLMJudgeService()),
        chat_service=ChatService(),
        docstore_service=docstore_service,
        reranking_service=RerankingService(),
        qa_dataset_service=QADatasetService(),
        qa_dataset_generation_service=QADatasetGenerationService(
            docstore_service=docstore_service,
            project_service=project_service,
        ),
        project_settings_repository=project_settings_repository,
        retrieval_settings_service=retrieval_settings_service,
    )


__all__ = ["BackendComposition", "build_backend_composition"]
