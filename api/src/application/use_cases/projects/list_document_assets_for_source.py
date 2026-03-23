from __future__ import annotations

from domain.common.ports import AssetRepositoryPort


class ListDocumentAssetsForSourceUseCase:
    """List SQLite multimodal assets for a single source filename in a project."""

    def __init__(self, *, asset_repository: AssetRepositoryPort) -> None:
        self._assets = asset_repository

    def execute(self, *, user_id: str, project_id: str, source_file: str) -> list[dict]:
        return self._assets.list_assets_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
        )
