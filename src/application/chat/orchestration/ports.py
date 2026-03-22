from __future__ import annotations

from typing import Any, Protocol

from src.domain.pipeline_payloads import PipelineBuildResult, SummaryRecallResult
from src.domain.project import Project
from src.domain.retrieval_filters import RetrievalFilters


class SummaryRecallStagePort(Protocol):
    def summary_recall_stage(
        self,
        project: Project,
        question: str,
        chat_history: list[str],
        *,
        enable_query_rewrite_override: bool | None,
        enable_hybrid_retrieval_override: bool | None,
        filters: RetrievalFilters | None,
        retrieval_settings: dict[str, Any] | None,
    ) -> SummaryRecallResult: ...


class PipelineAssemblyPort(Protocol):
    def build(
        self,
        *,
        project: Project,
        question: str,
        chat_history: list[str],
        recall: SummaryRecallResult,
        pipeline_started_monotonic: float,
    ) -> PipelineBuildResult | None: ...
