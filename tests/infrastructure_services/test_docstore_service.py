import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from src.core.exceptions import DocStoreError
from src.infrastructure.services.docstore_service import DocStoreService


class TestDocStoreService(unittest.TestCase):
    @patch("src.infrastructure.services.docstore_service.SQLiteDocStore")
    def test_save_asset_delegates_to_docstore(self, mock_store_cls):
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        service = DocStoreService()

        service.save_asset(
            doc_id="d1",
            user_id="u1",
            project_id="p1",
            source_file="file.pdf",
            content_type="text",
            raw_content="raw",
            summary="sum",
            metadata={"k": "v"},
        )

        mock_store.upsert_asset.assert_called_once()

    @patch("src.infrastructure.services.docstore_service.SQLiteDocStore")
    def test_upsert_asset_alias_calls_save_asset(self, mock_store_cls):
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        service = DocStoreService()
        service.upsert_asset(
            doc_id="d1",
            user_id="u1",
            project_id="p1",
            source_file="file.pdf",
            content_type="text",
            raw_content="raw",
            summary="sum",
            metadata=None,
        )
        mock_store.upsert_asset.assert_called_once()

    @patch("src.infrastructure.services.docstore_service.SQLiteDocStore")
    def test_get_asset_by_doc_id_wraps_errors(self, mock_store_cls):
        mock_store = MagicMock()
        mock_store.get_asset_by_doc_id.side_effect = RuntimeError("sqlite fail")
        mock_store_cls.return_value = mock_store
        service = DocStoreService()

        with self.assertRaises(DocStoreError):
            service.get_asset_by_doc_id("d1")

    @patch("src.infrastructure.services.docstore_service.SQLiteDocStore")
    def test_wrapper_methods_delegate_calls(self, mock_store_cls):
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        service = DocStoreService()

        method_calls = [
            ("get_assets_by_doc_ids", (["d1", "d2"],), {}),
            ("get_doc_ids_for_source_file", (), {"user_id": "u1", "project_id": "p1", "source_file": "f"}),
            ("count_assets_for_source_file", (), {"user_id": "u1", "project_id": "p1", "source_file": "f"}),
            ("get_asset_stats_for_source_file", (), {"user_id": "u1", "project_id": "p1", "source_file": "f"}),
            ("list_assets_for_source_file", (), {"user_id": "u1", "project_id": "p1", "source_file": "f"}),
            ("list_assets_for_project", (), {"user_id": "u1", "project_id": "p1"}),
            ("delete_assets_for_source_file", (), {"user_id": "u1", "project_id": "p1", "source_file": "f"}),
        ]

        for method_name, args, kwargs in method_calls:
            # One table-driven loop keeps wrapper coverage concise and explicit.
            with self.subTest(method=method_name):
                getattr(service, method_name)(*args, **kwargs)
                getattr(mock_store, method_name).assert_called()


if __name__ == "__main__":
    unittest.main()
