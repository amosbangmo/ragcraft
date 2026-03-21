import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from datetime import datetime, timezone

from src.infrastructure.logging.query_log_repository import QueryLogRepository
from src.infrastructure.persistence.sqlite.query_log_repository import SQLiteQueryLogRepository
from src.infrastructure.persistence.db import init_app_db
from src.services.query_log_service import QueryLogService, parse_query_log_timestamp


class TestSQLiteQueryLogRepository(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._prev_sqlite = os.environ.get("SQLITE_DB_PATH")
        os.environ["SQLITE_DB_PATH"] = str(Path(self._tmpdir.name) / "query_logs_test.db")

        def _restore() -> None:
            if self._prev_sqlite is None:
                os.environ.pop("SQLITE_DB_PATH", None)
            else:
                os.environ["SQLITE_DB_PATH"] = self._prev_sqlite

        self.addCleanup(_restore)
        init_app_db()

    def test_insert_list_roundtrip_json_lists(self) -> None:
        repo = SQLiteQueryLogRepository()
        repo.log(
            {
                "question": "q1",
                "timestamp": "2025-01-01T12:00:00+00:00",
                "project_id": "p1",
                "user_id": "u1",
                "selected_doc_ids": ["d1", "d2"],
                "retrieved_doc_ids": ["r1"],
                "query_intent": "factual",
            }
        )
        rows = repo.list_logs(project_id="p1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["selected_doc_ids"], ["d1", "d2"])
        self.assertEqual(rows[0]["retrieved_doc_ids"], ["r1"])
        self.assertEqual(rows[0]["timestamp"], "2025-01-01T12:00:00+00:00")
        self.assertEqual(rows[0].get("query_intent"), "factual")

    def test_insert_retrieval_strategy_roundtrip(self) -> None:
        repo = SQLiteQueryLogRepository()
        repo.log(
            {
                "question": "q2",
                "timestamp": "2025-01-02T12:00:00+00:00",
                "project_id": "p2",
                "user_id": "u2",
                "retrieval_strategy": {
                    "k": 8,
                    "use_hybrid": True,
                    "apply_filters": False,
                },
            }
        )
        rows = repo.list_logs(project_id="p2")
        self.assertEqual(len(rows), 1)
        rs = rows[0].get("retrieval_strategy")
        self.assertIsInstance(rs, dict)
        assert isinstance(rs, dict)
        self.assertEqual(rs.get("k"), 8)
        self.assertTrue(rs.get("use_hybrid"))
        self.assertFalse(rs.get("apply_filters"))

    def test_insert_table_aware_flag_roundtrip(self) -> None:
        repo = SQLiteQueryLogRepository()
        repo.log(
            {
                "question": "q_ta",
                "timestamp": "2025-04-01T12:00:00+00:00",
                "project_id": "p_ta",
                "user_id": "u_ta",
                "table_aware_qa_enabled": True,
            }
        )
        rows = repo.list_logs(project_id="p_ta")
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].get("table_aware_qa_enabled"))

    def test_insert_context_compression_roundtrip(self) -> None:
        repo = SQLiteQueryLogRepository()
        repo.log(
            {
                "question": "q_cc",
                "timestamp": "2025-03-01T12:00:00+00:00",
                "project_id": "p_cc",
                "user_id": "u_cc",
                "context_compression_chars_before": 1200,
                "context_compression_chars_after": 400,
                "context_compression_ratio": 0.3333,
            }
        )
        rows = repo.list_logs(project_id="p_cc")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].get("context_compression_chars_before"), 1200)
        self.assertEqual(rows[0].get("context_compression_chars_after"), 400)
        self.assertAlmostEqual(float(rows[0].get("context_compression_ratio", 0)), 0.3333, places=3)

    def test_list_logs_user_and_limit(self) -> None:
        repo = SQLiteQueryLogRepository()
        for i, uid in enumerate(["u1", "u1", "u2"]):
            repo.log(
                {
                    "question": f"q{i}",
                    "timestamp": f"2025-06-{10+i:02d}T12:00:00+00:00",
                    "project_id": "px",
                    "user_id": uid,
                }
            )
        rows = repo.list_logs(project_id="px", user_id="u1", limit=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["user_id"], "u1")


class TestQueryLogServiceSqlite(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._prev_sqlite = os.environ.get("SQLITE_DB_PATH")
        os.environ["SQLITE_DB_PATH"] = str(Path(self._tmpdir.name) / "query_logs_svc_test.db")

        def _restore() -> None:
            if self._prev_sqlite is None:
                os.environ.pop("SQLITE_DB_PATH", None)
            else:
                os.environ["SQLITE_DB_PATH"] = self._prev_sqlite

        self.addCleanup(_restore)
        init_app_db()

    def test_default_repository_sqlite_load_logs(self) -> None:
        svc = QueryLogService()
        svc.log_query(
            payload={
                "question": "hello",
                "project_id": "p9",
                "user_id": "u9",
                "timestamp": "2025-03-01T10:00:00+00:00",
                "latency_ms": 5,
            }
        )
        rows = svc.load_logs(project_id="p9")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["question"], "hello")
        self.assertEqual(rows[0]["latency_ms"], 5)

    def test_import_legacy_file_logs(self) -> None:
        with TemporaryDirectory() as tmp:
            legacy_path = Path(tmp) / "old.jsonl"
            repo = QueryLogRepository(log_path=legacy_path)
            repo.log(
                {
                    "question": "fromfile",
                    "project_id": "pimp",
                    "user_id": "u1",
                    "timestamp": "2024-01-02T12:00:00+00:00",
                }
            )
            svc = QueryLogService()
            n = svc.import_legacy_file_logs(log_path=legacy_path)
            self.assertEqual(n, 1)
            rows = svc.load_logs(project_id="pimp")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["question"], "fromfile")


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

    def test_build_entry_stores_query_intent_when_valid(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.json"
            repo = QueryLogRepository(log_path=path)
            service = QueryLogService(repository=repo)
            service.log_query(
                payload={
                    "question": "q",
                    "project_id": "p1",
                    "user_id": "u1",
                    "query_intent": "comparison",
                }
            )
            rows = repo.list_logs()
            self.assertEqual(rows[0]["query_intent"], "comparison")

    def test_build_entry_omits_invalid_query_intent(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.json"
            repo = QueryLogRepository(log_path=path)
            service = QueryLogService(repository=repo)
            service.log_query(
                payload={
                    "question": "q",
                    "project_id": "p1",
                    "user_id": "u1",
                    "query_intent": "not-a-real-intent",
                }
            )
            rows = repo.list_logs()
            self.assertNotIn("query_intent", rows[0])

    def test_build_entry_stores_retrieval_strategy(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.json"
            repo = QueryLogRepository(log_path=path)
            service = QueryLogService(repository=repo)
            service.log_query(
                payload={
                    "question": "q",
                    "project_id": "p1",
                    "user_id": "u1",
                    "retrieval_strategy": {
                        "k": 5,
                        "use_hybrid": False,
                        "apply_filters": True,
                    },
                }
            )
            rows = repo.list_logs()
            self.assertEqual(
                rows[0].get("retrieval_strategy"),
                {"k": 5, "use_hybrid": False, "apply_filters": True},
            )


if __name__ == "__main__":
    unittest.main()
