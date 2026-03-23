import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from infrastructure.persistence.db import init_app_db
from infrastructure.persistence.sqlite.qa_dataset_repository import (
    SQLiteQADatasetRepository as QADatasetRepository,
)


class TestQADatasetRepository(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._prev = os.environ.get("SQLITE_DB_PATH")
        os.environ["SQLITE_DB_PATH"] = str(Path(self._tmpdir.name) / "qa_repo_test.db")

        def _restore() -> None:
            if self._prev is None:
                os.environ.pop("SQLITE_DB_PATH", None)
            else:
                os.environ["SQLITE_DB_PATH"] = self._prev

        self.addCleanup(_restore)
        init_app_db()
        self.repo = QADatasetRepository()

    def test_create_list_get_update_delete(self) -> None:
        eid = self.repo.create_entry(
            user_id="u1",
            project_id="p1",
            question="What?",
            expected_answer="Because",
            expected_doc_ids=["d1"],
            expected_sources=["a.pdf"],
        )
        self.assertGreater(eid, 0)
        rows = self.repo.list_entries(user_id="u1", project_id="p1")
        self.assertEqual(len(rows), 1)
        got = self.repo.get_entry_by_id(entry_id=eid, user_id="u1", project_id="p1")
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got["question"], "What?")

        ok = self.repo.update_entry(
            entry_id=eid,
            user_id="u1",
            project_id="p1",
            question="Why?",
            expected_answer=None,
            expected_doc_ids=[],
            expected_sources=[],
        )
        self.assertTrue(ok)
        refreshed = self.repo.get_entry_by_id(entry_id=eid, user_id="u1", project_id="p1")
        self.assertIsNotNone(refreshed)
        assert refreshed is not None
        self.assertEqual(refreshed["question"], "Why?")
        self.assertIsNone(refreshed["expected_answer"])

        self.assertTrue(self.repo.delete_entry(entry_id=eid, user_id="u1", project_id="p1"))
        self.assertIsNone(self.repo.get_entry_by_id(entry_id=eid, user_id="u1", project_id="p1"))

    def test_get_update_delete_wrong_scope(self) -> None:
        eid = self.repo.create_entry(
            user_id="u1",
            project_id="p1",
            question="Q",
            expected_answer=None,
            expected_doc_ids=None,
            expected_sources=None,
        )
        self.assertIsNone(self.repo.get_entry_by_id(entry_id=eid, user_id="other", project_id="p1"))
        self.assertFalse(
            self.repo.update_entry(
                entry_id=eid,
                user_id="other",
                project_id="p1",
                question="Nope",
            )
        )
        self.assertFalse(self.repo.delete_entry(entry_id=eid, user_id="other", project_id="p1"))

    def test_delete_all_entries(self) -> None:
        self.repo.create_entry(user_id="u1", project_id="p1", question="a", expected_answer=None)
        self.repo.create_entry(user_id="u1", project_id="p1", question="b", expected_answer=None)
        n = self.repo.delete_all_entries(user_id="u1", project_id="p1")
        self.assertEqual(n, 2)
        self.assertEqual(len(self.repo.list_entries(user_id="u1", project_id="p1")), 0)


if __name__ == "__main__":
    unittest.main()
