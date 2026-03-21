import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.infrastructure.docstore.sqlite_docstore import SQLiteDocStore
from src.infrastructure.persistence.db import init_app_db


class TestSQLiteDocStore(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._prev = os.environ.get("SQLITE_DB_PATH")
        os.environ["SQLITE_DB_PATH"] = str(Path(self._tmpdir.name) / "docstore_test.db")

        def _restore() -> None:
            if self._prev is None:
                os.environ.pop("SQLITE_DB_PATH", None)
            else:
                os.environ["SQLITE_DB_PATH"] = self._prev

        self.addCleanup(_restore)
        init_app_db()
        self.store = SQLiteDocStore()

    def test_upsert_get_roundtrip(self) -> None:
        self.store.upsert_asset(
            doc_id="d1",
            user_id="u1",
            project_id="p1",
            source_file="a.pdf",
            content_type="text",
            raw_content="body",
            summary="sum",
            metadata={"page_number": 3},
        )
        row = self.store.get_asset_by_doc_id("d1")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["metadata"]["page_number"], 3)

    def test_get_asset_missing_returns_none(self) -> None:
        self.assertIsNone(self.store.get_asset_by_doc_id("nope"))

    def test_get_assets_by_doc_ids_order_and_empty(self) -> None:
        self.store.upsert_asset(
            doc_id="x1",
            user_id="u1",
            project_id="p1",
            source_file="f.pdf",
            content_type="text",
            raw_content="a",
            summary="s",
            metadata={},
        )
        self.store.upsert_asset(
            doc_id="x2",
            user_id="u1",
            project_id="p1",
            source_file="f.pdf",
            content_type="table",
            raw_content="t",
            summary="s",
            metadata={},
        )
        out = self.store.get_assets_by_doc_ids(["x2", "x1", "missing"])
        self.assertEqual([r["doc_id"] for r in out], ["x2", "x1"])
        self.assertEqual(self.store.get_assets_by_doc_ids([]), [])

    def test_list_count_stats_delete_for_source_file(self) -> None:
        self.store.upsert_asset(
            doc_id="t1",
            user_id="u1",
            project_id="p1",
            source_file="doc.pdf",
            content_type="text",
            raw_content="a",
            summary="s",
            metadata={},
        )
        self.store.upsert_asset(
            doc_id="t2",
            user_id="u1",
            project_id="p1",
            source_file="doc.pdf",
            content_type="image",
            raw_content="b",
            summary="s",
            metadata={},
        )
        ids = self.store.get_doc_ids_for_source_file(
            user_id="u1", project_id="p1", source_file="doc.pdf"
        )
        self.assertEqual(ids, ["t1", "t2"])
        self.assertEqual(
            self.store.count_assets_for_source_file(
                user_id="u1", project_id="p1", source_file="doc.pdf"
            ),
            2,
        )
        stats = self.store.get_asset_stats_for_source_file(
            user_id="u1", project_id="p1", source_file="doc.pdf"
        )
        self.assertEqual(stats["text_count"], 1)
        self.assertEqual(stats["image_count"], 1)
        self.assertEqual(stats["table_count"], 0)
        self.assertIsNotNone(stats["latest_ingested_at"])

        listed = self.store.list_assets_for_source_file(
            user_id="u1", project_id="p1", source_file="doc.pdf"
        )
        self.assertEqual(len(listed), 2)

        n = self.store.delete_assets_for_source_file(
            user_id="u1", project_id="p1", source_file="doc.pdf"
        )
        self.assertEqual(n, 2)
        self.assertEqual(
            self.store.count_assets_for_source_file(
                user_id="u1", project_id="p1", source_file="doc.pdf"
            ),
            0,
        )

    def test_list_assets_for_project(self) -> None:
        self.store.upsert_asset(
            doc_id="p1a",
            user_id="u1",
            project_id="prj",
            source_file="one.txt",
            content_type="text",
            raw_content="a",
            summary="s",
            metadata=None,
        )
        rows = self.store.list_assets_for_project(user_id="u1", project_id="prj")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_file"], "one.txt")

    def test_upsert_updates_same_doc_id(self) -> None:
        self.store.upsert_asset(
            doc_id="same",
            user_id="u1",
            project_id="p1",
            source_file="a.pdf",
            content_type="text",
            raw_content="v1",
            summary="s",
            metadata={},
        )
        self.store.upsert_asset(
            doc_id="same",
            user_id="u1",
            project_id="p1",
            source_file="b.pdf",
            content_type="text",
            raw_content="v2",
            summary="s2",
            metadata={"k": 1},
        )
        row = self.store.get_asset_by_doc_id("same")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["source_file"], "b.pdf")
        self.assertEqual(row["raw_content"], "v2")


if __name__ == "__main__":
    unittest.main()
