from __future__ import annotations

from collections.abc import Callable

from src.application.use_cases.projects.resolve_project import ResolveProjectUseCase


class InvalidateProjectChainCacheUseCase:
    """
    Drop the in-process vector-store handle for a project (see ``ProjectChainHandleCachePort``).

    The injected ``invalidate_project_chain`` callable is wired at the composition root: FastAPI passes
    ``ProcessProjectChainCache.drop``; Streamlit builds may compose additional session eviction.
    """

    def __init__(
        self,
        *,
        resolve_project: ResolveProjectUseCase,
        invalidate_project_chain: Callable[[str], None],
    ) -> None:
        self._resolve_project = resolve_project
        self._invalidate = invalidate_project_chain

    def execute(self, *, user_id: str, project_id: str) -> None:
        project = self._resolve_project.execute(user_id, project_id)
        self._invalidate(project.project_id)
