from __future__ import annotations

from src.services.docstore_service import DocStoreService


class ListDocumentAssetsForSourceUseCase:
    """List SQLite multimodal assets for a single source filename in a project."""

    def __init__(self, *, docstore_service: DocStoreService) -> None:
        self._docstore = docstore_service

    def execute(self, *, user_id: str, project_id: str, source_file: str) -> list[dict]:
        return self._docstore.list_assets_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
        )
