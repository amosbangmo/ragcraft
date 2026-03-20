import json
from datetime import datetime

from src.infrastructure.persistence.db import get_connection


class QADatasetRepository:
    def create_entry(
        self,
        *,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ) -> int:
        conn = get_connection()
        cursor = conn.execute(
            """
            INSERT INTO qa_dataset (
                user_id,
                project_id,
                question,
                expected_answer,
                expected_doc_ids_json,
                expected_sources_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                project_id,
                question,
                expected_answer,
                json.dumps(expected_doc_ids or []),
                json.dumps(expected_sources or []),
                datetime.utcnow().isoformat(),
                None,
            ),
        )
        conn.commit()
        entry_id = int(cursor.lastrowid)
        conn.close()
        return entry_id

    def list_entries(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT
                id,
                user_id,
                project_id,
                question,
                expected_answer,
                expected_doc_ids_json,
                expected_sources_json,
                created_at,
                updated_at
            FROM qa_dataset
            WHERE user_id = ?
              AND project_id = ?
            ORDER BY id ASC
            """,
            (user_id, project_id),
        ).fetchall()
        conn.close()

        return [
            {
                "id": int(row["id"]),
                "user_id": row["user_id"],
                "project_id": row["project_id"],
                "question": row["question"],
                "expected_answer": row["expected_answer"],
                "expected_doc_ids": json.loads(row["expected_doc_ids_json"] or "[]"),
                "expected_sources": json.loads(row["expected_sources_json"] or "[]"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def get_entry_by_id(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
    ) -> dict | None:
        conn = get_connection()
        row = conn.execute(
            """
            SELECT
                id,
                user_id,
                project_id,
                question,
                expected_answer,
                expected_doc_ids_json,
                expected_sources_json,
                created_at,
                updated_at
            FROM qa_dataset
            WHERE id = ?
              AND user_id = ?
              AND project_id = ?
            """,
            (entry_id, user_id, project_id),
        ).fetchone()
        conn.close()

        if not row:
            return None

        return {
            "id": int(row["id"]),
            "user_id": row["user_id"],
            "project_id": row["project_id"],
            "question": row["question"],
            "expected_answer": row["expected_answer"],
            "expected_doc_ids": json.loads(row["expected_doc_ids_json"] or "[]"),
            "expected_sources": json.loads(row["expected_sources_json"] or "[]"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def update_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ) -> bool:
        conn = get_connection()
        cursor = conn.execute(
            """
            UPDATE qa_dataset
            SET
                question = ?,
                expected_answer = ?,
                expected_doc_ids_json = ?,
                expected_sources_json = ?,
                updated_at = ?
            WHERE id = ?
              AND user_id = ?
              AND project_id = ?
            """,
            (
                question,
                expected_answer,
                json.dumps(expected_doc_ids or []),
                json.dumps(expected_sources or []),
                datetime.utcnow().isoformat(),
                entry_id,
                user_id,
                project_id,
            ),
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def delete_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
    ) -> bool:
        conn = get_connection()
        cursor = conn.execute(
            """
            DELETE FROM qa_dataset
            WHERE id = ?
              AND user_id = ?
              AND project_id = ?
            """,
            (entry_id, user_id, project_id),
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def delete_all_entries(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> int:
        conn = get_connection()
        cursor = conn.execute(
            """
            DELETE FROM qa_dataset
            WHERE user_id = ?
              AND project_id = ?
            """,
            (user_id, project_id),
        )
        conn.commit()
        deleted_count = int(cursor.rowcount or 0)
        conn.close()
        return deleted_count
