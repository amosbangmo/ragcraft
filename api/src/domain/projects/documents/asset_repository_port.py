from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AssetRepositoryPort(Protocol):
    """Persistence for raw RAG assets (chunk rows) keyed by doc_id and project scope."""

    def upsert_asset(
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
    ) -> None: ...

    def get_asset_by_doc_id(self, doc_id: str) -> dict | None: ...

    def get_assets_by_doc_ids(self, doc_ids: list[str]) -> list[dict]: ...

    def get_doc_ids_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> list[str]: ...

    def count_assets_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> int: ...

    def get_asset_stats_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> dict: ...

    def list_assets_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> list[dict]: ...

    def list_assets_for_project(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> list[dict]: ...

    def delete_assets_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> int: ...
