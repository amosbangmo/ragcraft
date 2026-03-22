"""Compare FAISS-only vs hybrid retrieval for a set of questions (no LLM answer)."""

from __future__ import annotations

from src.application.projects.use_cases.resolve_project import ResolveProjectUseCase
from src.infrastructure.services.retrieval_comparison_service import RetrievalComparisonService


class CompareRetrievalModesUseCase:
    def __init__(
        self,
        *,
        resolve_project: ResolveProjectUseCase,
        comparison_service: RetrievalComparisonService,
    ) -> None:
        self._resolve_project = resolve_project
        self._comparison = comparison_service

    def execute(
        self,
        *,
        user_id: str,
        project_id: str,
        questions: list[str],
        enable_query_rewrite: bool,
    ) -> dict:
        project = self._resolve_project.execute(user_id, project_id)
        return self._comparison.compare(
            project=project,
            questions=list(questions),
            enable_query_rewrite=bool(enable_query_rewrite),
        )
