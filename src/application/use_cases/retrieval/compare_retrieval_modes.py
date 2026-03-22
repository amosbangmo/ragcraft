"""Compare FAISS-only vs hybrid retrieval for a set of questions (no LLM answer)."""

from __future__ import annotations

from typing import Any

from src.application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
from src.application.use_cases.projects.resolve_project import ResolveProjectUseCase
from src.application.use_cases.retrieval.retrieval_mode_comparison import (
    compare_retrieval_modes_for_project,
)


class CompareRetrievalModesUseCase:
    def __init__(
        self,
        *,
        resolve_project: ResolveProjectUseCase,
        inspect_pipeline: InspectRagPipelineUseCase,
    ) -> None:
        self._resolve_project = resolve_project
        self._inspect_pipeline = inspect_pipeline

    def execute(
        self,
        *,
        user_id: str,
        project_id: str,
        questions: list[str],
        enable_query_rewrite: bool,
    ) -> dict[str, Any]:
        project = self._resolve_project.execute(user_id, project_id)

        def _inspect(
            proj,
            question: str,
            chat_history,
            *,
            enable_query_rewrite_override: bool | None = None,
            enable_hybrid_retrieval_override: bool | None = None,
            filters=None,
            retrieval_settings=None,
        ):
            return self._inspect_pipeline.execute(
                proj,
                question,
                chat_history,
                filters=filters,
                retrieval_settings=retrieval_settings,
                enable_query_rewrite_override=enable_query_rewrite_override,
                enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
            )

        return compare_retrieval_modes_for_project(
            inspect_pipeline=_inspect,
            project=project,
            questions=list(questions),
            enable_query_rewrite=bool(enable_query_rewrite),
        )
