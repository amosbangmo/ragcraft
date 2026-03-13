from src.infrastructure.docstore.sqlite_docstore import SQLiteDocStore


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

    def get_asset_by_doc_id(self, doc_id: str):
        return self.docstore.get_asset_by_doc_id(doc_id)

    def get_assets_by_doc_ids(self, doc_ids: list[str]) -> list[dict]:
        return self.docstore.get_assets_by_doc_ids(doc_ids)
