import uuid
from datetime import datetime

from src.infrastructure.persistence.db import get_connection


class UserRepository:
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
        created_at = datetime.utcnow().isoformat()

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

    def update_profile(self, user_id: str, username: str, display_name: str):
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

    def update_password(self, user_id: str, password_hash: str):
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

    def update_avatar_path(self, user_id: str, avatar_path: str | None):
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

    def delete_user(self, user_id: str):
        conn = get_connection()
        conn.execute(
            """
            DELETE FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        )
        conn.commit()
        conn.close()
