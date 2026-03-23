import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from infrastructure.persistence.db import init_app_db
from infrastructure.evaluation.qa_dataset_service import QADatasetService


class TestQADatasetServicePersistence(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._prev = os.environ.get("SQLITE_DB_PATH")
        os.environ["SQLITE_DB_PATH"] = str(Path(self._tmpdir.name) / "qa_service_test.db")

        def _restore() -> None:
            if self._prev is None:
                os.environ.pop("SQLITE_DB_PATH", None)
            else:
                os.environ["SQLITE_DB_PATH"] = self._prev

        self.addCleanup(_restore)
        init_app_db()
        self.svc = QADatasetService()

    def test_create_requires_question(self) -> None:
        with self.assertRaises(ValueError):
            self.svc.create_entry(
                user_id="u1",
                project_id="p1",
                question="   ",
            )

    def test_create_list_update_delete_and_keys(self) -> None:
        e = self.svc.create_entry(
            user_id="u1",
            project_id="p1",
            question="  Hello?  ",
            expected_answer=" Yes ",
            expected_doc_ids=["d1", "d1", ""],
            expected_sources=["a.pdf", "a.pdf"],
        )
        self.assertEqual(e.question, "Hello?")
        self.assertEqual(e.expected_answer, "Yes")
        self.assertEqual(e.expected_doc_ids, ["d1"])
        self.assertEqual(e.expected_sources, ["a.pdf"])

        keys = self.svc.existing_question_keys(user_id="u1", project_id="p1")
        self.assertIn(self.svc.normalized_question_key("hello?"), keys)

        updated = self.svc.update_entry(
            entry_id=e.id,
            user_id="u1",
            project_id="p1",
            question="Why?",
        )
        self.assertEqual(updated.question, "Why?")

        self.assertTrue(
            self.svc.delete_entry(entry_id=e.id, user_id="u1", project_id="p1")
        )

        with self.assertRaises(ValueError):
            self.svc.delete_entry(entry_id=e.id, user_id="u1", project_id="p1")

    def test_update_not_found(self) -> None:
        with self.assertRaises(ValueError):
            self.svc.update_entry(
                entry_id=99999,
                user_id="u1",
                project_id="p1",
                question="x",
            )

    def test_delete_all_entries(self) -> None:
        self.svc.create_entry(user_id="u1", project_id="p1", question="q1")
        self.svc.create_entry(user_id="u1", project_id="p1", question="q2")
        self.assertEqual(
            self.svc.delete_all_entries(user_id="u1", project_id="p1"), 2
        )


if __name__ == "__main__":
    unittest.main()
