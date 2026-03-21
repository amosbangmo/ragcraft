"""
Backend composition root: explicit wiring for services used by Streamlit and FastAPI.

Construction order (high level):
1. Persistence bootstrap (SQLite app DB).
2. Core adapters: project paths, doc store, vector store, ingestion, auth.
3. Shared ``QueryLogService`` (single instance per composition; injected into ``RAGService``).
4. ``RAGService`` (lazy): retrieval settings, pipeline / ask use cases, query logging.
5. ``RetrievalComparisonService`` (lazy): depends on ``RAGService``.

Use cases are not all constructed here: many are built in :class:`~src.app.ragcraft_app.RAGCraftApp`
methods or in FastAPI ``Depends`` getters. This module owns **service-level** singletons per
composition instance.
"""

from __future__ import annotations

from src.auth.auth_service import AuthService
from src.infrastructure.persistence.db import init_app_db
from src.services.chat_service import ChatService
from src.services.docstore_service import DocStoreService
from src.services.evaluation_service import EvaluationService
from src.services.ingestion_service import IngestionService
from src.services.llm_judge_service import LLMJudgeService
from src.services.project_service import ProjectService
from src.services.project_settings_service import ProjectSettingsService
from src.services.qa_dataset_generation_service import QADatasetGenerationService
from src.services.qa_dataset_service import QADatasetService
from src.services.query_log_service import QueryLogService
from src.services.rag_service import RAGService
from src.services.reranking_service import RerankingService
from src.services.retrieval_comparison_service import RetrievalComparisonService
from src.services.retrieval_settings_service import RetrievalSettingsService
from src.services.vectorstore_service import VectorStoreService


class BackendComposition:
    """Wired backend services for one application instance (session or API process)."""

    def __init__(self) -> None:
        init_app_db()

        self.query_log_service = QueryLogService()

        self.auth_service = AuthService()
        self.project_service = ProjectService()
        self.ingestion_service = IngestionService()
        self.vectorstore_service = VectorStoreService()
        self.evaluation_service = EvaluationService(llm_judge_service=LLMJudgeService())
        self.chat_service = ChatService()
        self.docstore_service = DocStoreService()
        self.reranking_service = RerankingService()
        self.qa_dataset_service = QADatasetService()
        self.qa_dataset_generation_service = QADatasetGenerationService(
            docstore_service=self.docstore_service,
            project_service=self.project_service,
        )
        self.project_settings_service = ProjectSettingsService()

        self._rag_service: RAGService | None = None
        self._retrieval_comparison_service: RetrievalComparisonService | None = None

    @property
    def rag_service(self) -> RAGService:
        if self._rag_service is None:
            self._rag_service = RAGService(
                vectorstore_service=self.vectorstore_service,
                evaluation_service=self.evaluation_service,
                docstore_service=self.docstore_service,
                reranking_service=self.reranking_service,
                query_log_service=self.query_log_service,
                retrieval_settings_service=RetrievalSettingsService(
                    project_settings_service=self.project_settings_service,
                ),
            )
        return self._rag_service

    @property
    def retrieval_comparison_service(self) -> RetrievalComparisonService:
        if self._retrieval_comparison_service is None:
            self._retrieval_comparison_service = RetrievalComparisonService(
                rag_service=self.rag_service,
            )
        return self._retrieval_comparison_service


def build_backend_composition() -> BackendComposition:
    """Factory for a new wired graph (Streamlit session, tests, or explicit injection)."""
    return BackendComposition()
