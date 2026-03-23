"""SQLite user repository adapter (isolated DB file)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from infrastructure.auth.password_utils import hash_password, verify_password
from infrastructure.persistence.db import get_connection, init_app_db
from infrastructure.persistence.sqlite.user_repository import SqliteUserRepository


class TestSqliteUserRepository(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "users_test.db"
        self._patcher = patch(
            "infrastructure.persistence.db.get_sqlite_db_path",
            return_value=self.db_path,
        )
        self._patcher.start()
        init_app_db()
        self.repo = SqliteUserRepository()

    def tearDown(self) -> None:
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_create_roundtrip_and_password_verify(self) -> None:
        h = hash_password("secret123")
        self.repo.create_user(username="alice", password_hash=h, display_name="Alice")
        row = self.repo.get_by_username("alice")
        assert row is not None
        self.assertTrue(verify_password("secret123", row["password_hash"]))
        by_id = self.repo.get_by_user_id(str(row["user_id"]))
        assert by_id is not None
        self.assertEqual(str(by_id["username"]), "alice")

    def test_delete_user_cascades_related_tables(self) -> None:
        h = hash_password("pw")
        created = self.repo.create_user(
            username="bob", password_hash=h, display_name="Bob"
        )
        uid = str(created["user_id"])
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO rag_assets (
                doc_id, user_id, project_id, source_file, content_type,
                raw_content, summary, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "d1",
                uid,
                "p1",
                "f.txt",
                "text/plain",
                "x",
                "s",
                None,
                "2020-01-01",
            ),
        )
        conn.execute(
            """
            INSERT INTO qa_dataset (
                user_id, project_id, question, expected_answer,
                expected_doc_ids_json, expected_sources_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, "p1", "q", None, None, None, "2020-01-01"),
        )
        conn.execute(
            """
            INSERT INTO query_logs (
                user_id, project_id, question, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (uid, "p1", "q", "2020-01-01"),
        )
        conn.execute(
            """
            INSERT INTO project_retrieval_settings (
                user_id, project_id, retrieval_preset, retrieval_advanced,
                enable_query_rewrite, enable_hybrid_retrieval, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, "p1", "balanced", 0, 1, 1, "2020-01-01"),
        )
        conn.commit()
        conn.close()

        self.repo.delete_user(uid)

        self.assertIsNone(self.repo.get_by_user_id(uid))
        conn2 = get_connection()
        try:
            self.assertEqual(
                conn2.execute(
                    "SELECT COUNT(*) FROM rag_assets WHERE user_id = ?", (uid,)
                ).fetchone()[0],
                0,
            )
            self.assertEqual(
                conn2.execute(
                    "SELECT COUNT(*) FROM qa_dataset WHERE user_id = ?", (uid,)
                ).fetchone()[0],
                0,
            )
            self.assertEqual(
                conn2.execute(
                    "SELECT COUNT(*) FROM query_logs WHERE user_id = ?", (uid,)
                ).fetchone()[0],
                0,
            )
            self.assertEqual(
                conn2.execute(
                    "SELECT COUNT(*) FROM project_retrieval_settings WHERE user_id = ?",
                    (uid,),
                ).fetchone()[0],
                0,
            )
        finally:
            conn2.close()


if __name__ == "__main__":
    unittest.main()
