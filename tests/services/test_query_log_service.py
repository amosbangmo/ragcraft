import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from src.infrastructure.logging.query_log_repository import QueryLogRepository
from src.services.query_log_service import QueryLogService


class TestQueryLogRepository(unittest.TestCase):
    def test_append_and_list(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "query_logs.json"
            repo = QueryLogRepository(log_path=path)
            repo.log({"project_id": "p1", "question": "a"})
            repo.log({"project_id": "p2", "question": "b"})
            all_rows = repo.list_logs()
            self.assertEqual(len(all_rows), 2)
            p1 = repo.list_logs(project_id="p1")
            self.assertEqual(len(p1), 1)
            self.assertEqual(p1[0]["question"], "a")


class TestQueryLogService(unittest.TestCase):
    def test_build_entry_truncates_and_normalizes(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.json"
            repo = QueryLogRepository(log_path=path)
            service = QueryLogService(repository=repo)
            long_q = "x" * 3000
            service.log_query(
                payload={
                    "question": long_q,
                    "rewritten_query": "rw",
                    "project_id": "p1",
                    "user_id": "u1",
                    "selected_doc_ids": ["a", "b"],
                    "retrieved_doc_ids": ["a"],
                    "latency_ms": 12.7,
                    "confidence": 0.5,
                    "answer": "short",
                }
            )
            rows = repo.list_logs()
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]["question"].endswith("…"))
            self.assertLessEqual(len(rows[0]["question"]), 2000)
            self.assertEqual(rows[0]["latency_ms"], 13)
            self.assertEqual(rows[0]["confidence"], 0.5)
            self.assertIn("timestamp", rows[0])

    def test_log_query_swallows_repository_errors(self):
        repo = MagicMock()
        repo.log.side_effect = OSError("boom")
        service = QueryLogService(repository=repo)
        service.log_query(payload={"question": "q"})


if __name__ == "__main__":
    unittest.main()
