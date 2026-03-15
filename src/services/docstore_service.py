from src.infrastructure.docstore.sqlite_docstore import SQLiteDocStore
from src.core.exceptions import DocStoreError


class DocStoreService:
    def __init__(self):
        self.docstore = SQLiteDocStore()

    def save_asset(
        self,
        *,
        doc_id: str,
        user_id: str,
        project_id: str,
        source_file: str,
        content_type: str,
        raw_content: str,
        summary: str,
        metadata: dict | None = None,
    ) -> None:
        try:
            self.docstore.upsert_asset(
                doc_id=doc_id,
                user_id=user_id,
                project_id=project_id,
                source_file=source_file,
                content_type=content_type,
                raw_content=raw_content,
                summary=summary,
                metadata=metadata,
            )
        except Exception as exc:
            raise DocStoreError(
                f"Failed to save asset '{doc_id}' in SQLite docstore: {exc}",
                user_message="Unable to save extracted assets in the SQLite document store.",
            ) from exc

    def get_asset_by_doc_id(self, doc_id: str):
        try:
            return self.docstore.get_asset_by_doc_id(doc_id)
        except Exception as exc:
            raise DocStoreError(
                f"Failed to read asset '{doc_id}' from SQLite docstore: {exc}",
                user_message="Unable to read an asset from the SQLite document store.",
            ) from exc

    def get_assets_by_doc_ids(self, doc_ids: list[str]) -> list[dict]:
        try:
            return self.docstore.get_assets_by_doc_ids(doc_ids)
        except Exception as exc:
            raise DocStoreError(
                f"Failed to read assets by doc_ids from SQLite docstore: {exc}",
                user_message="Unable to read retrieved assets from the SQLite document store.",
            ) from exc

    def get_doc_ids_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> list[str]:
        try:
            return self.docstore.get_doc_ids_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=source_file,
            )
        except Exception as exc:
            raise DocStoreError(
                f"Failed to read doc_ids for source_file '{source_file}' from SQLite docstore: {exc}",
                user_message="Unable to read document asset identifiers from the SQLite document store.",
            ) from exc

    def count_assets_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> int:
        try:
            return self.docstore.count_assets_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=source_file,
            )
        except Exception as exc:
            raise DocStoreError(
                f"Failed to count assets for source_file '{source_file}' in SQLite docstore: {exc}",
                user_message="Unable to count document assets from the SQLite document store.",
            ) from exc

    def get_asset_stats_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> dict:
        try:
            return self.docstore.get_asset_stats_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=source_file,
            )
        except Exception as exc:
            raise DocStoreError(
                f"Failed to read asset stats for source_file '{source_file}' from SQLite docstore: {exc}",
                user_message="Unable to read asset statistics from the SQLite document store.",
            ) from exc

    def list_assets_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> list[dict]:
        try:
            return self.docstore.list_assets_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=source_file,
            )
        except Exception as exc:
            raise DocStoreError(
                f"Failed to list assets for source_file '{source_file}' from SQLite docstore: {exc}",
                user_message="Unable to inspect assets from the SQLite document store.",
            ) from exc

    def list_assets_for_project(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> list[dict]:
        try:
            return self.docstore.list_assets_for_project(
                user_id=user_id,
                project_id=project_id,
            )
        except Exception as exc:
            raise DocStoreError(
                f"Failed to list assets for project '{project_id}' from SQLite docstore: {exc}",
                user_message="Unable to inspect project assets from the SQLite document store.",
            ) from exc

    def delete_assets_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> int:
        try:
            return self.docstore.delete_assets_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=source_file,
            )
        except Exception as exc:
            raise DocStoreError(
                f"Failed to delete assets for source_file '{source_file}' from SQLite docstore: {exc}",
                user_message="Unable to delete assets from the SQLite document store.",
            ) from exc
