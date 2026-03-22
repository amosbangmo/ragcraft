from __future__ import annotations

from src.application.use_cases.projects.resolve_project import ResolveProjectUseCase
from src.domain.ports import AssetRepositoryPort


class GetProjectDocumentDetailsUseCase:
    """Build document listing rows (paths, sizes, asset stats) for a project root directory."""

    def __init__(self, *, resolve_project: ResolveProjectUseCase, asset_repository: AssetRepositoryPort) -> None:
        self._resolve_project = resolve_project
        self._assets = asset_repository

    def execute(self, *, user_id: str, project_id: str, document_names: list[str]) -> list[dict]:
        project = self._resolve_project.execute(user_id, project_id)
        details: list[dict] = []

        for doc_name in document_names:
            file_path = project.path / doc_name
            asset_count = self._assets.count_assets_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=doc_name,
            )
            asset_stats = self._assets.get_asset_stats_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=doc_name,
            )
            details.append(
                {
                    "name": doc_name,
                    "project_id": project_id,
                    "path": str(file_path),
                    "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
                    "asset_count": asset_count,
                    "text_count": int(asset_stats.get("text_count", 0)),
                    "table_count": int(asset_stats.get("table_count", 0)),
                    "image_count": int(asset_stats.get("image_count", 0)),
                    "latest_ingested_at": asset_stats.get("latest_ingested_at"),
                }
            )

        return details
