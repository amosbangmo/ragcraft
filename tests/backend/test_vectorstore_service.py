import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

if "langchain_core.documents" not in sys.modules:
    # Provide a tiny stand-in so tests can run without LangChain installed.
    langchain_core_module = types.ModuleType("langchain_core")
    documents_module = types.ModuleType("langchain_core.documents")

    class Document:
        def __init__(self, page_content: str, metadata: dict | None = None):
            self.page_content = page_content
            self.metadata = metadata or {}

    documents_module.Document = Document
    langchain_core_module.documents = documents_module
    sys.modules["langchain_core"] = langchain_core_module
    sys.modules["langchain_core.documents"] = documents_module

if "src.infrastructure.vectorstores.faiss.vector_store" not in sys.modules:
    # Replace FAISS helpers with no-op functions to keep tests unit-level.
    faiss_store_module = types.ModuleType("src.infrastructure.vectorstores.faiss.vector_store")

    def _noop(*args, **kwargs):
        return None

    faiss_store_module.load_vector_store = _noop
    faiss_store_module.save_vector_store = _noop
    faiss_store_module.create_or_update_vector_store = _noop
    faiss_store_module.delete_documents_from_vector_store = _noop
    sys.modules["src.infrastructure.vectorstores.faiss.vector_store"] = faiss_store_module

from langchain_core.documents import Document
from src.core.exceptions import VectorStoreError
from src.domain.project import Project
from src.infrastructure.caching.process_project_chain_cache import ProcessProjectChainCache
from src.backend.vectorstore_service import VectorStoreService


class TestVectorStoreService(unittest.TestCase):
    def setUp(self):
        self._chain_cache = ProcessProjectChainCache()
        self.service = VectorStoreService(chain_cache=self._chain_cache)
        self.project = Project(user_id="u1", project_id="p1")

    @patch("src.backend.vectorstore_service.load_vector_store")
    def test_load_returns_vector_store(self, mock_load):
        vector_store = MagicMock()
        mock_load.return_value = vector_store

        result = self.service.load(self.project)

        self.assertIs(result, vector_store)
        mock_load.assert_called_once_with(self.project.faiss_index_path)

    @patch("src.backend.vectorstore_service.load_vector_store")
    def test_load_uses_cache_until_dropped(self, mock_load):
        vector_store = MagicMock()
        mock_load.return_value = vector_store

        first = self.service.load(self.project)
        second = self.service.load(self.project)
        self.assertIs(first, second)
        mock_load.assert_called_once_with(self.project.faiss_index_path)

        self._chain_cache.drop(self.project.project_id)
        self.service.load(self.project)
        self.assertEqual(mock_load.call_count, 2)

    @patch("src.backend.vectorstore_service.load_vector_store")
    def test_load_wraps_errors(self, mock_load):
        mock_load.side_effect = RuntimeError("boom")

        with self.assertRaises(VectorStoreError):
            self.service.load(self.project)

    @patch("src.backend.vectorstore_service.create_or_update_vector_store")
    def test_index_documents_returns_empty_tuple_for_empty_chunks(self, mock_create_or_update):
        # Empty input should short-circuit and avoid touching infrastructure.
        store, indexing_ms = self.service.index_documents(self.project, [])

        self.assertIsNone(store)
        self.assertEqual(indexing_ms, 0.0)
        mock_create_or_update.assert_not_called()

    @patch("src.backend.vectorstore_service.save_vector_store")
    @patch("src.backend.vectorstore_service.create_or_update_vector_store")
    def test_index_documents_saves_vector_store_when_created(self, mock_create_or_update, mock_save):
        chunks = [Document(page_content="chunk", metadata={"doc_id": "d1"})]
        vector_store = MagicMock()
        mock_create_or_update.return_value = vector_store

        store, indexing_ms = self.service.index_documents(self.project, chunks)

        self.assertIs(store, vector_store)
        self.assertGreaterEqual(indexing_ms, 0.0)
        mock_save.assert_called_once_with(vector_store, self.project.faiss_index_path)

    def test_similarity_search_returns_empty_when_store_missing(self):
        with patch.object(self.service, "load", return_value=None):
            result = self.service.similarity_search(self.project, "query", k=3)

        self.assertEqual(result, [])

    def test_similarity_search_re_raises_vectorstore_error(self):
        with patch.object(self.service, "load", side_effect=VectorStoreError("x")):
            with self.assertRaises(VectorStoreError):
                self.service.similarity_search(self.project, "query", k=3)

    def test_similarity_search_wraps_unexpected_error(self):
        vector_store = MagicMock()
        vector_store.similarity_search.side_effect = RuntimeError("db down")

        with patch.object(self.service, "load", return_value=vector_store):
            with self.assertRaises(VectorStoreError):
                self.service.similarity_search(self.project, "query", k=3)


if __name__ == "__main__":
    unittest.main()
