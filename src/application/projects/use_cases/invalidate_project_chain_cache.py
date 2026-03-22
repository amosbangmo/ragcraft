from __future__ import annotations

from collections.abc import Callable

from src.services.project_service import ProjectService


class InvalidateProjectChainCacheUseCase:
    """
    Drop the in-process vector-store handle for a project (see ``ProjectChainHandleCachePort``).

    The injected ``invalidate_project_chain`` callable is wired at the composition root: FastAPI passes
    ``ProcessProjectChainCache.drop``; Streamlit builds may compose additional session eviction.
    """

    def __init__(
        self,
        *,
        project_service: ProjectService,
        invalidate_project_chain: Callable[[str], None],
    ) -> None:
        self._project_service = project_service
        self._invalidate = invalidate_project_chain

    def execute(self, *, user_id: str, project_id: str) -> None:
        project = self._project_service.get_project(user_id, project_id)
        self._invalidate(project.project_id)
