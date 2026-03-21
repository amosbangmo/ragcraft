import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from datetime import datetime, timezone

from src.infrastructure.logging.query_log_repository import QueryLogRepository
from src.services.query_log_service import QueryLogService, parse_query_log_timestamp


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

    def test_build_entry_includes_stage_latencies_when_present(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.json"
            repo = QueryLogRepository(log_path=path)
            service = QueryLogService(repository=repo)
            service.log_query(
                payload={
                    "question": "q",
                    "project_id": "p1",
                    "user_id": "u1",
                    "latency_ms": 100.2,
                    "query_rewrite_ms": 1.2,
                    "retrieval_ms": 2.3,
                    "reranking_ms": 3.4,
                    "prompt_build_ms": 4.5,
                    "answer_generation_ms": 88.6,
                    "total_latency_ms": 100.2,
                }
            )
            rows = repo.list_logs()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["query_rewrite_ms"], 1)
            self.assertEqual(rows[0]["retrieval_ms"], 2)
            self.assertEqual(rows[0]["total_latency_ms"], 100)

    def test_log_query_swallows_repository_errors(self):
        repo = MagicMock()
        repo.log.side_effect = OSError("boom")
        service = QueryLogService(repository=repo)
        service.log_query(payload={"question": "q"})

    def test_load_logs_last_n_and_date_filter(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.json"
            repo = QueryLogRepository(log_path=path)
            service = QueryLogService(repository=repo)
            t0 = "2024-01-01T12:00:00+00:00"
            t1 = "2024-06-01T12:00:00+00:00"
            t2 = "2024-12-01T12:00:00+00:00"
            for ts, q in [(t0, "a"), (t1, "b"), (t2, "c")]:
                service.log_query(
                    payload={
                        "question": q,
                        "project_id": "p1",
                        "user_id": "u1",
                        "timestamp": ts,
                        "latency_ms": 10,
                    }
                )
            rows = service.load_logs(project_id="p1", last_n=2)
            self.assertEqual([r["question"] for r in rows], ["c", "b"])
            since = datetime(2024, 3, 1, tzinfo=timezone.utc)
            until = datetime(2024, 9, 1, tzinfo=timezone.utc)
            mid = service.load_logs(project_id="p1", since_utc=since, until_utc=until)
            self.assertEqual(len(mid), 1)
            self.assertEqual(mid[0]["question"], "b")

    def test_parse_query_log_timestamp_z_suffix(self):
        dt = parse_query_log_timestamp({"timestamp": "2020-05-05T10:00:00Z"})
        self.assertIsNotNone(dt)
        assert dt is not None
        self.assertEqual(dt.year, 2020)
        self.assertEqual(dt.month, 5)

    def test_build_entry_stores_hybrid_fields(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.json"
            repo = QueryLogRepository(log_path=path)
            service = QueryLogService(repository=repo)
            service.log_query(
                payload={
                    "question": "q",
                    "project_id": "p1",
                    "user_id": "u1",
                    "hybrid_retrieval_enabled": True,
                    "retrieval_mode": "faiss+bm25",
                }
            )
            rows = repo.list_logs()
            self.assertTrue(rows[0]["hybrid_retrieval_enabled"])
            self.assertEqual(rows[0]["retrieval_mode"], "faiss+bm25")


if __name__ == "__main__":
    unittest.main()
