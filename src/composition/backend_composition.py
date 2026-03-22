"""
Backend service graph: persistence bootstrap, infrastructure adapters, and orchestration services.

Construction is **deterministic** and centralized in :func:`build_backend_composition`. Application
use cases are composed in :mod:`src.composition.application_container` on top of this graph.

Layers (in build order):
1. SQLite app DB (:func:`~src.infrastructure.persistence.db.init_app_db`).
2. Core services: auth, projects, ingestion, vector store, evaluation, chat, doc store, reranking,
   QA dataset + generation, project settings, retrieval settings merge.
3. Shared :class:`~src.infrastructure.adapters.query_logging.query_log_service.QueryLogService`.
4. RAG retrieval subgraph — lazily instantiated on first access to defer heavy LangChain wiring
   (see :mod:`src.composition.chat_rag_wiring`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.adapters.sqlite.project_settings_repository import SqliteProjectSettingsRepository
from src.adapters.sqlite.user_repository import SqliteUserRepository
from src.auth.auth_service import AuthService
from src.domain.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from src.infrastructure.persistence.db import init_app_db
from src.infrastructure.adapters.chat.chat_service import ChatService
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
    from src.composition.chat_rag_wiring import RagRetrievalSubgraph
    from src.infrastructure.adapters.document.ingestion_service import IngestionService
    from src.infrastructure.adapters.rag.vectorstore_service import VectorStoreService


@dataclass
class BackendComposition:
    """
    Immutable service graph for one application instance (API process or Streamlit session).

    ``rag_retrieval_subgraph`` is built on first read; all other references are fixed at
    construction time.
    """

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
    _rag_retrieval_subgraph: RagRetrievalSubgraph | None = field(default=None, init=False, repr=False)

    @property
    def rag_retrieval_subgraph(self) -> RagRetrievalSubgraph:
        if self._rag_retrieval_subgraph is None:
            from src.composition.chat_rag_wiring import build_rag_retrieval_subgraph

            self._rag_retrieval_subgraph = build_rag_retrieval_subgraph(
                vectorstore_service=self.vectorstore_service,
                docstore_service=self.docstore_service,
                reranking_service=self.reranking_service,
                retrieval_settings_service=self.retrieval_settings_service,
            )
        return self._rag_retrieval_subgraph


def build_backend_composition() -> BackendComposition:
    """Assemble the service-level composition root (no use cases)."""
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
