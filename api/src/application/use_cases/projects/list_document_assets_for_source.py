from __future__ import annotations

from domain.common.ports import AssetRepositoryPort
from domain.projects.documents.stored_multimodal_asset import StoredMultimodalAsset


class ListDocumentAssetsForSourceUseCase:
    """List SQLite multimodal assets for a single source filename in a project."""

    def __init__(self, *, asset_repository: AssetRepositoryPort) -> None:
        self._assets = asset_repository

    def execute(self, *, user_id: str, project_id: str, source_file: str) -> list[StoredMultimodalAsset]:
        rows = self._assets.list_assets_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
        )
        return [StoredMultimodalAsset.from_mapping(r) for r in rows]
