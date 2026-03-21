from __future__ import annotations

from src.services.docstore_service import DocStoreService
from src.services.project_service import ProjectService


class GetProjectDocumentDetailsUseCase:
    """Build document listing rows (paths, sizes, asset stats) for a project root directory."""

    def __init__(self, *, project_service: ProjectService, docstore_service: DocStoreService) -> None:
        self._project_service = project_service
        self._docstore = docstore_service

    def execute(self, *, user_id: str, project_id: str, document_names: list[str]) -> list[dict]:
        project = self._project_service.get_project(user_id, project_id)
        details: list[dict] = []

        for doc_name in document_names:
            file_path = project.path / doc_name
            asset_count = self._docstore.count_assets_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=doc_name,
            )
            asset_stats = self._docstore.get_asset_stats_for_source_file(
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
