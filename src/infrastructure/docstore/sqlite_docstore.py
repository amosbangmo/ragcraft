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
                doc_id,
                user_id,
                project_id,
                source_file,
                content_type,
                raw_content,
                summary,
                metadata_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                user_id = excluded.user_id,
                project_id = excluded.project_id,
                source_file = excluded.source_file,
                content_type = excluded.content_type,
                raw_content = excluded.raw_content,
                summary = excluded.summary,
                metadata_json = excluded.metadata_json
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
            SELECT
                doc_id,
                user_id,
                project_id,
                source_file,
                content_type,
                raw_content,
                summary,
                metadata_json,
                created_at
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
            "created_at": row["created_at"],
        }

    def get_assets_by_doc_ids(self, doc_ids: list[str]) -> list[dict]:
        assets_by_id = {}

        if not doc_ids:
            return []

        conn = get_connection()
        placeholders = ",".join(["?"] * len(doc_ids))

        rows = conn.execute(
            f"""
            SELECT
                doc_id,
                user_id,
                project_id,
                source_file,
                content_type,
                raw_content,
                summary,
                metadata_json,
                created_at
            FROM rag_assets
            WHERE doc_id IN ({placeholders})
            """,
            doc_ids,
        ).fetchall()
        conn.close()

        for row in rows:
            assets_by_id[row["doc_id"]] = {
                "doc_id": row["doc_id"],
                "user_id": row["user_id"],
                "project_id": row["project_id"],
                "source_file": row["source_file"],
                "content_type": row["content_type"],
                "raw_content": row["raw_content"],
                "summary": row["summary"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
                "created_at": row["created_at"],
            }

        return [assets_by_id[doc_id] for doc_id in doc_ids if doc_id in assets_by_id]

    def get_doc_ids_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> list[str]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT doc_id
            FROM rag_assets
            WHERE user_id = ?
              AND project_id = ?
              AND source_file = ?
            ORDER BY id ASC
            """,
            (user_id, project_id, source_file),
        ).fetchall()
        conn.close()

        return [row["doc_id"] for row in rows]

    def count_assets_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> int:
        conn = get_connection()
        row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM rag_assets
            WHERE user_id = ?
              AND project_id = ?
              AND source_file = ?
            """,
            (user_id, project_id, source_file),
        ).fetchone()
        conn.close()

        return int(row["total"]) if row else 0

    def get_asset_stats_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> dict:
        conn = get_connection()

        rows = conn.execute(
            """
            SELECT
                content_type,
                COUNT(*) AS total,
                MAX(created_at) AS latest_created_at
            FROM rag_assets
            WHERE user_id = ?
              AND project_id = ?
              AND source_file = ?
            GROUP BY content_type
            """,
            (user_id, project_id, source_file),
        ).fetchall()

        conn.close()

        stats = {
            "text_count": 0,
            "table_count": 0,
            "image_count": 0,
            "latest_ingested_at": None,
        }

        for row in rows:
            content_type = row["content_type"]
            total = int(row["total"] or 0)
            latest_created_at = row["latest_created_at"]

            if content_type == "text":
                stats["text_count"] = total
            elif content_type == "table":
                stats["table_count"] = total
            elif content_type == "image":
                stats["image_count"] = total

            if latest_created_at:
                if (
                    stats["latest_ingested_at"] is None
                    or latest_created_at > stats["latest_ingested_at"]
                ):
                    stats["latest_ingested_at"] = latest_created_at

        return stats

    def list_assets_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT
                doc_id,
                user_id,
                project_id,
                source_file,
                content_type,
                raw_content,
                summary,
                metadata_json,
                created_at
            FROM rag_assets
            WHERE user_id = ?
              AND project_id = ?
              AND source_file = ?
            ORDER BY id ASC
            """,
            (user_id, project_id, source_file),
        ).fetchall()
        conn.close()

        return [
            {
                "doc_id": row["doc_id"],
                "user_id": row["user_id"],
                "project_id": row["project_id"],
                "source_file": row["source_file"],
                "content_type": row["content_type"],
                "raw_content": row["raw_content"],
                "summary": row["summary"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def delete_assets_for_source_file(
        self,
        *,
        user_id: str,
        project_id: str,
        source_file: str,
    ) -> int:
        conn = get_connection()
        cursor = conn.execute(
            """
            DELETE FROM rag_assets
            WHERE user_id = ?
              AND project_id = ?
              AND source_file = ?
            """,
            (user_id, project_id, source_file),
        )
        conn.commit()
        deleted_count = cursor.rowcount
        conn.close()

        return deleted_count
