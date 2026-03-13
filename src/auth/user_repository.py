import uuid
from datetime import datetime, timezone

from src.auth.db import get_connection


class UserRepository:
    def get_by_username(self, username: str):
        conn = get_connection()
        row = conn.execute(
            """
            SELECT id, username, user_id, password_hash, display_name, created_at
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
        conn.close()
        return row

    def create_user(self, username: str, password_hash: str, display_name: str):
        user_id = str(uuid.uuid4())[:8]
        created_at = datetime.now(timezone.utc).isoformat()

        conn = get_connection()
        conn.execute(
            """
            INSERT INTO users (username, user_id, password_hash, display_name, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, user_id, password_hash, display_name, created_at),
        )
        conn.commit()
        conn.close()

        return {
            "username": username,
            "user_id": user_id,
            "display_name": display_name,
        }

    def username_exists(self, username: str) -> bool:
        return self.get_by_username(username) is not None
