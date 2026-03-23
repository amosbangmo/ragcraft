"""Ports for summary-recall technical steps (application boundary; implemented in infrastructure)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from domain.projects.project import Project
from domain.rag.retrieval_filters import RetrievalFilters
from domain.rag.retrieval_settings import RetrievalSettings
from domain.rag.summary_recall_document import SummaryRecallDocument


class QueryRewritePort(Protocol):
    def rewrite(
        self,
        *,
        question: str,
        chat_history: list[str],
        max_history_messages: int,
    ) -> str: ...


class SummaryVectorRecallPort(Protocol):
    def similarity_search(
        self,
        project: Project,
        query: str,
        k: int,
    ) -> list[SummaryRecallDocument]: ...


class SummaryLexicalRecallPort(Protocol):
    def lexical_summary_search(
        self,
        *,
        project: Project,
        query: str,
        settings: RetrievalSettings,
        filters: RetrievalFilters | None,
    ) -> list[SummaryRecallDocument]: ...


@dataclass(frozen=True)
class SummaryRecallTechnicalPorts:
    """Injected I/O for :class:`~application.use_cases.chat.orchestration.summary_recall_workflow.ApplicationSummaryRecallStage`."""

    query_rewrite: QueryRewritePort
    vector_recall: SummaryVectorRecallPort
    lexical_recall: SummaryLexicalRecallPort


def merge_summary_recall_documents(
    *,
    settings: RetrievalSettings,
    primary_docs: list[SummaryRecallDocument],
    secondary_docs: list[SummaryRecallDocument],
    max_docs: int | None = None,
) -> list[SummaryRecallDocument]:
    """Application-facing name for domain RRF merge (used by tests and callers)."""
    from domain.rag.summary_document_fusion import merge_summary_documents_weighted_rrf

    return merge_summary_documents_weighted_rrf(
        settings=settings,
        primary_docs=primary_docs,
        secondary_docs=secondary_docs,
        max_docs=max_docs,
    )
