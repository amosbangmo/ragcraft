"""
Backend service graph: persistence bootstrap and **technical** infrastructure adapters only.

Construction is **deterministic** in :func:`build_backend_composition`. Cross-cutting RAG/chat wiring
and use cases live in :mod:`composition.application_container` (and :mod:`composition.chat_rag_wiring`).

Layers (in build order):
1. SQLite app DB (:func:`~infrastructure.persistence.db.init_app_db`).
2. Adapters: auth, projects, ingestion, vector store, evaluation, chat transcript (port implementation),
   doc store, reranking, QA dataset + generation, project settings repository, retrieval settings, query logging.

**Orchestration inventory (this module):** none. RAG pipeline sequencing is **not** built here; only shared
technical services are. Target: keep this file free of chat/RAG flow logic — graph construction only.

**Target ownership:** RAG orchestration stays in application use cases (e.g. :class:`~application.use_cases.chat.build_rag_pipeline.BuildRagPipelineUseCase`, :class:`~application.use_cases.chat.ask_question.AskQuestionUseCase`); this module never calls those use cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from application.services.retrieval_settings_tuner import RetrievalSettingsTuner
from composition.evaluation_wiring import (
    build_evaluation_service,
    default_evaluation_wiring_parts,
)
from domain.common.ports.avatar_storage_port import AvatarStoragePort
from domain.common.ports.chat_transcript_port import ChatTranscriptPort
from domain.common.ports.password_hasher_port import PasswordHasherPort
from domain.common.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from infrastructure.auth.auth_service import AuthService
from infrastructure.auth.bcrypt_password_hasher import BcryptPasswordHasher
from infrastructure.auth.jwt_auth_settings import JwtAuthSettings
from infrastructure.auth.jwt_authentication_adapter import JwtAuthenticationAdapter
from infrastructure.evaluation.evaluation_service import EvaluationService
from infrastructure.evaluation.qa_dataset_generation_service import (
    QADatasetGenerationService,
)
from infrastructure.evaluation.qa_dataset_service import QADatasetService
from infrastructure.observability.query_log_service import QueryLogService
from infrastructure.persistence.db import init_app_db
from infrastructure.persistence.project_service import ProjectService
from infrastructure.persistence.sqlite.project_settings_repository import (
    SqliteProjectSettingsRepository,
)
from infrastructure.persistence.sqlite.user_repository import SqliteUserRepository
from infrastructure.rag.docstore_service import DocStoreService
from infrastructure.rag.reranking_service import RerankingService
from infrastructure.storage.file_avatar_storage import FileAvatarStorage

if TYPE_CHECKING:
    from infrastructure.rag.ingestion_service import IngestionService
    from infrastructure.rag.vectorstore_service import VectorStoreService


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
    retrieval_settings_tuner: RetrievalSettingsTuner


def build_backend_composition(
    *,
    chat_transcript: ChatTranscriptPort,
) -> BackendComposition:
    """
    Assemble technical adapters only (no application use cases).

    Callers supply :class:`~domain.common.ports.chat_transcript_port.ChatTranscriptPort` (e.g.
    :class:`~application.services.memory_chat_transcript.MemoryChatTranscript` for FastAPI/tests,
    or a gateway-built session transcript for Streamlit).
    """
    from infrastructure.rag.ingestion_service import IngestionService
    from infrastructure.rag.vectorstore_service import VectorStoreService

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
    retrieval_settings_tuner = RetrievalSettingsTuner(
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
        retrieval_settings_tuner=retrieval_settings_tuner,
    )


__all__ = ["BackendComposition", "build_backend_composition"]
