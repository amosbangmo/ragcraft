"""SQLite adapter for :class:`~domain.common.ports.user_repository_port.UserRepositoryPort`."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from infrastructure.persistence.db import get_connection


class SqliteUserRepository:
    def get_by_username(self, username: str):
        conn = get_connection()
        row = conn.execute(
            """
            SELECT id, username, user_id, password_hash, display_name, avatar_path, created_at
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
        conn.close()
        return row

    def get_by_user_id(self, user_id: str):
        conn = get_connection()
        row = conn.execute(
            """
            SELECT id, username, user_id, password_hash, display_name, avatar_path, created_at
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        conn.close()
        return row

    def create_user(self, username: str, password_hash: str, display_name: str):
        user_id = str(uuid.uuid4())[:8]
        created_at = datetime.now(timezone.utc).isoformat()

        conn = get_connection()
        conn.execute(
            """
            INSERT INTO users (username, user_id, password_hash, display_name, avatar_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, user_id, password_hash, display_name, None, created_at),
        )
        conn.commit()
        conn.close()

        return {
            "username": username,
            "user_id": user_id,
            "display_name": display_name,
            "avatar_path": None,
        }

    def username_exists(self, username: str) -> bool:
        return self.get_by_username(username) is not None

    def update_profile(self, user_id: str, username: str, display_name: str) -> None:
        conn = get_connection()
        conn.execute(
            """
            UPDATE users
            SET username = ?, display_name = ?
            WHERE user_id = ?
            """,
            (username, display_name, user_id),
        )
        conn.commit()
        conn.close()

    def update_password(self, user_id: str, password_hash: str) -> None:
        conn = get_connection()
        conn.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE user_id = ?
            """,
            (password_hash, user_id),
        )
        conn.commit()
        conn.close()

    def update_avatar_path(self, user_id: str, avatar_path: str | None) -> None:
        conn = get_connection()
        conn.execute(
            """
            UPDATE users
            SET avatar_path = ?
            WHERE user_id = ?
            """,
            (avatar_path, user_id),
        )
        conn.commit()
        conn.close()

    def delete_user(self, user_id: str) -> None:
        """
        Remove the account row and all SQLite rows scoped to ``user_id`` (RAG assets, QA rows,
        query logs, per-project retrieval settings). Disk cleanup is done by
        :meth:`~infrastructure.storage.file_avatar_storage.FileAvatarStorage.delete_user_data_tree`
        in :class:`~application.use_cases.users.delete_user_account.DeleteUserAccountUseCase`.
        """
        conn = get_connection()
        try:
            conn.execute("DELETE FROM rag_assets WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM qa_dataset WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM query_logs WHERE user_id = ?", (user_id,))
            conn.execute(
                "DELETE FROM project_retrieval_settings WHERE user_id = ?", (user_id,)
            )
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()
