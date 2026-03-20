import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("OPENAI_API_KEY", "test-key")

if "langchain_core.documents" not in sys.modules:
    # Provide a local Document fallback when LangChain is unavailable.
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

if "src.core.config" not in sys.modules:
    # Minimal config used by the service constructor in tests.
    config_module = types.ModuleType("src.core.config")
    config_module.INGESTION_CONFIG = types.SimpleNamespace(
        extraction_max_text_chars_per_asset=2500,
        summary_max_input_chars=4000,
    )
    sys.modules["src.core.config"] = config_module

if "src.infrastructure.ingestion.loader" not in sys.modules:
    # Stub external ingestion modules to avoid importing heavy dependencies.
    loader_module = types.ModuleType("src.infrastructure.ingestion.loader")
    loader_module.save_uploaded_file = lambda uploaded_file, path: path
    sys.modules["src.infrastructure.ingestion.loader"] = loader_module

if "src.infrastructure.ingestion.unstructured_extractor" not in sys.modules:
    extractor_module = types.ModuleType("src.infrastructure.ingestion.unstructured_extractor")
    extractor_module.extract_elements = lambda file_path, source_file: []
    sys.modules["src.infrastructure.ingestion.unstructured_extractor"] = extractor_module

if "src.infrastructure.ingestion.summarizer" not in sys.modules:
    summarizer_module = types.ModuleType("src.infrastructure.ingestion.summarizer")

    class ElementSummarizer:
        def summarize(self, *, content_type: str, raw_content: str, metadata: dict):
            return raw_content

    summarizer_module.ElementSummarizer = ElementSummarizer
    sys.modules["src.infrastructure.ingestion.summarizer"] = summarizer_module

from src.core.exceptions import DocumentExtractionError, LLMServiceError, OCRDependencyError
from src.domain.project import Project
from src.services.ingestion_service import IngestionService


class TestIngestionService(unittest.TestCase):
    def setUp(self):
        self.service = IngestionService()
        self.service.summarizer = MagicMock()
        self.project = Project(user_id="u1", project_id="p1")

    @patch("src.services.ingestion_service.extract_elements")
    def test_ingest_file_path_builds_documents_and_assets(self, mock_extract):
        mock_extract.return_value = [
            {
                "doc_id": "d1",
                "content_type": "text",
                "raw_content": "raw text",
                "metadata": {"page_number": 2},
            }
        ]
        self.service.summarizer.summarize.return_value = "summary text"

        docs, assets = self.service.ingest_file_path(
            project=self.project,
            file_path=Path("x.pdf"),
            source_file="x.pdf",
        )

        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].page_content, "summary text")
        self.assertEqual(docs[0].metadata["doc_id"], "d1")
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["summary"], "summary text")
        self.assertEqual(assets[0]["project_id"], "p1")

    @patch("src.services.ingestion_service.extract_elements")
    def test_ingest_file_path_raises_on_empty_elements(self, mock_extract):
        mock_extract.return_value = []

        with self.assertRaises(DocumentExtractionError):
            self.service.ingest_file_path(
                project=self.project,
                file_path=Path("x.pdf"),
                source_file="x.pdf",
            )

    @patch("src.services.ingestion_service.extract_elements")
    def test_ingest_file_path_translates_ocr_signature_errors(self, mock_extract):
        # Service detects known OCR error signatures and maps them to domain error.
        mock_extract.side_effect = RuntimeError("Tesseract is not installed")

        with self.assertRaises(OCRDependencyError):
            self.service.ingest_file_path(
                project=self.project,
                file_path=Path("x.pdf"),
                source_file="x.pdf",
            )

    @patch("src.services.ingestion_service.extract_elements")
    def test_ingest_file_path_wraps_summarizer_errors(self, mock_extract):
        mock_extract.return_value = [
            {
                "doc_id": "d1",
                "content_type": "text",
                "raw_content": "raw text",
                "metadata": {},
            }
        ]
        self.service.summarizer.summarize.side_effect = RuntimeError("llm fail")

        with self.assertRaises(LLMServiceError):
            self.service.ingest_file_path(
                project=self.project,
                file_path=Path("x.pdf"),
                source_file="x.pdf",
            )


if __name__ == "__main__":
    unittest.main()
