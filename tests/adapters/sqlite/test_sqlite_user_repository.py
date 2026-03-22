"""SQLite user repository adapter (isolated DB file)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.adapters.sqlite.user_repository import SqliteUserRepository
from src.auth.password_utils import hash_password, verify_password
from src.infrastructure.persistence.db import init_app_db


class TestSqliteUserRepository(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "users_test.db"
        self._patcher = patch(
            "src.infrastructure.persistence.db.get_sqlite_db_path",
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


if __name__ == "__main__":
    unittest.main()
