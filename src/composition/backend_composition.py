"""
Backend service graph: persistence bootstrap and **technical** infrastructure adapters only.

Construction is **deterministic** in :func:`build_backend_composition`. Cross-cutting RAG/chat wiring
and use cases live in :mod:`src.composition.application_container` (and :mod:`src.composition.chat_rag_wiring`).

Layers (in build order):
1. SQLite app DB (:func:`~src.infrastructure.persistence.db.init_app_db`).
2. Adapters: auth, projects, ingestion, vector store, evaluation, chat transcript (port implementation),
   doc store, reranking, QA dataset + generation, project settings repository, retrieval settings, query logging.

**Orchestration inventory (this module):** none. RAG pipeline sequencing is **not** built here; only shared
technical services are. Target: keep this file free of chat/RAG flow logic — graph construction only.

**Target ownership:** RAG orchestration stays in application use cases (e.g. :class:`~src.application.use_cases.chat.build_rag_pipeline.BuildRagPipelineUseCase`, :class:`~src.application.use_cases.chat.ask_question.AskQuestionUseCase`); this module never calls those use cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.infrastructure.adapters.sqlite.project_settings_repository import SqliteProjectSettingsRepository
from src.infrastructure.adapters.sqlite.user_repository import SqliteUserRepository
from src.infrastructure.adapters.auth.bcrypt_password_hasher import BcryptPasswordHasher
from src.infrastructure.adapters.filesystem.file_avatar_storage import FileAvatarStorage
from src.auth.auth_service import AuthService
from src.domain.ports.avatar_storage_port import AvatarStoragePort
from src.domain.ports.chat_transcript_port import ChatTranscriptPort
from src.domain.ports.password_hasher_port import PasswordHasherPort
from src.domain.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from src.infrastructure.persistence.db import init_app_db
from src.infrastructure.adapters.rag.docstore_service import DocStoreService
from src.composition.evaluation_wiring import build_evaluation_service, default_evaluation_wiring_parts
from src.infrastructure.adapters.evaluation.evaluation_service import EvaluationService
from src.infrastructure.adapters.workspace.project_service import ProjectService
from src.infrastructure.adapters.qa_dataset.qa_dataset_generation_service import QADatasetGenerationService
from src.infrastructure.adapters.qa_dataset.qa_dataset_service import QADatasetService
from src.infrastructure.adapters.query_logging.query_log_service import QueryLogService
from src.infrastructure.adapters.rag.reranking_service import RerankingService
from src.infrastructure.adapters.rag.retrieval_settings_service import RetrievalSettingsService
from src.infrastructure.adapters.auth.jwt_auth_settings import JwtAuthSettings
from src.infrastructure.adapters.auth.jwt_authentication_adapter import JwtAuthenticationAdapter

if TYPE_CHECKING:
    from src.infrastructure.adapters.document.ingestion_service import IngestionService
    from src.infrastructure.adapters.rag.vectorstore_service import VectorStoreService


@dataclass
class BackendComposition:
    """Immutable graph of technical dependencies for one process (API or Streamlit)."""

    bearer_token_auth: JwtAuthenticationAdapter
    query_log_service: QueryLogService
    password_hasher: PasswordHasherPort
    avatar_storage: AvatarStoragePort
    auth_service: AuthService
    project_service: ProjectService
    ingestion_service: IngestionService
    vectorstore_service: VectorStoreService
    evaluation_service: EvaluationService
    chat_transcript: ChatTranscriptPort
    docstore_service: DocStoreService
    reranking_service: RerankingService
    qa_dataset_service: QADatasetService
    qa_dataset_generation_service: QADatasetGenerationService
    project_settings_repository: ProjectSettingsRepositoryPort
    retrieval_settings_service: RetrievalSettingsService


def build_backend_composition(
    *,
    chat_transcript: ChatTranscriptPort,
) -> BackendComposition:
    """
    Assemble technical adapters only (no application use cases).

    Callers supply :class:`~src.domain.ports.chat_transcript_port.ChatTranscriptPort` (e.g.
    :class:`~src.application.frontend_support.memory_chat_transcript.MemoryChatTranscript` for FastAPI,
    :class:`~src.infrastructure.adapters.chat_transcript.MemoryChatTranscript` for tests or adapter-local defaults, or a
    gateway-built session transcript for Streamlit).
    """
    from src.infrastructure.adapters.document.ingestion_service import IngestionService
    from src.infrastructure.adapters.rag.vectorstore_service import VectorStoreService

    init_app_db()

    jwt_settings = JwtAuthSettings.from_env()
    bearer_token_auth = JwtAuthenticationAdapter(jwt_settings)

    password_hasher = BcryptPasswordHasher()
    avatar_storage = FileAvatarStorage()
    user_repository = SqliteUserRepository()
    query_log_service = QueryLogService()
    project_service = ProjectService()
    docstore_service = DocStoreService()
    project_settings_repository = SqliteProjectSettingsRepository()
    retrieval_settings_service = RetrievalSettingsService(
        project_settings_repository=project_settings_repository,
    )

    return BackendComposition(
        bearer_token_auth=bearer_token_auth,
        query_log_service=query_log_service,
        password_hasher=password_hasher,
        avatar_storage=avatar_storage,
        auth_service=AuthService(user_repository=user_repository, password_hasher=password_hasher),
        project_service=project_service,
        ingestion_service=IngestionService(),
        vectorstore_service=VectorStoreService(),
        evaluation_service=build_evaluation_service(default_evaluation_wiring_parts()),
        chat_transcript=chat_transcript,
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
