import json
from datetime import datetime

from src.auth.db import get_connection


class SQLiteDocStore:
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
    ) -> None:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO rag_assets (
                doc_id, user_id, project_id, source_file,
                content_type, raw_content, summary, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                user_id=excluded.user_id,
                project_id=excluded.project_id,
                source_file=excluded.source_file,
                content_type=excluded.content_type,
                raw_content=excluded.raw_content,
                summary=excluded.summary,
                metadata_json=excluded.metadata_json
            """,
            (
                doc_id,
                user_id,
                project_id,
                source_file,
                content_type,
                raw_content,
                summary,
                json.dumps(metadata or {}),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def get_asset_by_doc_id(self, doc_id: str):
        conn = get_connection()
        row = conn.execute(
            """
            SELECT doc_id, user_id, project_id, source_file,
                   content_type, raw_content, summary, metadata_json
            FROM rag_assets
            WHERE doc_id = ?
            """,
            (doc_id,),
        ).fetchone()
        conn.close()

        if not row:
            return None

        return {
            "doc_id": row["doc_id"],
            "user_id": row["user_id"],
            "project_id": row["project_id"],
            "source_file": row["source_file"],
            "content_type": row["content_type"],
            "raw_content": row["raw_content"],
            "summary": row["summary"],
            "metadata": json.loads(row["metadata_json"] or "{}"),
        }

    def get_assets_by_doc_ids(self, doc_ids: list[str]) -> list[dict]:
        assets = []
        for doc_id in doc_ids:
            asset = self.get_asset_by_doc_id(doc_id)
            if asset:
                assets.append(asset)
        return assets
