import unittest
from unittest.mock import MagicMock, patch

from infrastructure.rag.llm.qa_dataset_llm_gateway import extract_json_array
from infrastructure.evaluation.qa_dataset_generation_service import (
    MAX_CONTEXT_CHARS,
    QADatasetGenerationService,
)


class TestQADatasetGenerationService(unittest.TestCase):
    def _svc(self, docstore: MagicMock, project: MagicMock) -> QADatasetGenerationService:
        return QADatasetGenerationService(
            docstore_service=docstore,
            project_service=project,
        )

    def test_resolve_source_files_all_and_filter(self) -> None:
        docstore = MagicMock()
        project = MagicMock()
        project.list_project_documents.return_value = ["b.pdf", "a.pdf"]
        svc = self._svc(docstore, project)

        all_files = svc._resolve_source_files(
            user_id="u", project_id="p", source_files=None
        )
        self.assertEqual(all_files, ["b.pdf", "a.pdf"])

        filtered = svc._resolve_source_files(
            user_id="u",
            project_id="p",
            source_files=["  a.pdf  ", "nope", "a.pdf", "", None],
        )
        self.assertEqual(filtered, ["a.pdf"])

        project.list_project_documents.return_value = []
        self.assertEqual(
            svc._resolve_source_files(user_id="u", project_id="p", source_files=None),
            [],
        )

    def test_generate_entries_errors_without_docs_or_assets(self) -> None:
        docstore = MagicMock()
        project = MagicMock()
        project.list_project_documents.return_value = []
        svc = self._svc(docstore, project)
        with self.assertRaisesRegex(ValueError, "No project documents"):
            svc.generate_entries(
                user_id="u", project_id="p", num_questions=3, source_files=None
            )

        project.list_project_documents.return_value = ["f.pdf"]
        docstore.list_assets_for_source_file.return_value = []
        with self.assertRaisesRegex(ValueError, "No indexed assets"):
            svc.generate_entries(
                user_id="u", project_id="p", num_questions=1, source_files=None
            )

    @patch("infrastructure.rag.llm.qa_dataset_llm_gateway.LLM")
    def test_generate_entries_success_and_clamp(self, mock_llm) -> None:
        mock_llm.invoke.return_value = MagicMock(
            content='[{"question":"Q1","expected_answer":"A1","expected_doc_ids":["d1"],"expected_sources":["f.pdf"]}]'
        )
        docstore = MagicMock()
        docstore.list_assets_for_source_file.return_value = [
            {
                "doc_id": "d1",
                "content_type": "text",
                "source_file": "f.pdf",
                "metadata": {"page_number": 1, "start_element_index": 0, "end_element_index": 2},
                "summary": "S",
                "raw_content": "hello world",
            },
        ]
        project = MagicMock()
        project.list_project_documents.return_value = ["f.pdf"]
        svc = self._svc(docstore, project)

        out = svc.generate_entries(
            user_id="u", project_id="p", num_questions=50, source_files=None
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].question, "Q1")

    @patch("infrastructure.rag.llm.qa_dataset_llm_gateway.LLM")
    def test_parse_json_with_fence_and_skips_bad_items(self, mock_llm) -> None:
        payload = """```json
[{"question":"ok","expected_answer":"","expected_doc_ids":[],"expected_sources":[]},{"not":"dict"},""]
```"""
        mock_llm.invoke.return_value = MagicMock(content=payload)
        docstore = MagicMock()
        docstore.list_assets_for_source_file.return_value = [
            {
                "doc_id": "d1",
                "content_type": "table",
                "source_file": "f.pdf",
                "metadata": {
                    "table_title": "T",
                    "table_text": "cell",
                    "page_start": 1,
                    "page_end": 2,
                },
                "summary": "",
                "raw_content": "",
            },
        ]
        project = MagicMock()
        project.list_project_documents.return_value = ["f.pdf"]
        svc = self._svc(docstore, project)
        out = svc.generate_entries(
            user_id="u", project_id="p", num_questions=5, source_files=None
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].question, "ok")

    @patch("infrastructure.rag.llm.qa_dataset_llm_gateway.LLM")
    def test_invalid_json_and_empty_entries_raise(self, mock_llm) -> None:
        docstore = MagicMock()
        docstore.list_assets_for_source_file.return_value = [
            {
                "doc_id": "d1",
                "content_type": "image",
                "source_file": "f.pdf",
                "metadata": {"image_title": "Fig 1", "page_start": 3},
                "summary": "cap",
                "raw_content": "",
            },
        ]
        project = MagicMock()
        project.list_project_documents.return_value = ["f.pdf"]
        svc = self._svc(docstore, project)

        mock_llm.invoke.return_value = MagicMock(content="not json")
        with self.assertRaises(ValueError):
            svc.generate_entries(
                user_id="u", project_id="p", num_questions=1, source_files=None
            )

        mock_llm.invoke.return_value = MagicMock(content='{"a":1}')
        with self.assertRaisesRegex(ValueError, "JSON array"):
            svc.generate_entries(
                user_id="u", project_id="p", num_questions=1, source_files=None
            )

        mock_llm.invoke.return_value = MagicMock(content="[]")
        with self.assertRaisesRegex(ValueError, "did not return any valid"):
            svc.generate_entries(
                user_id="u", project_id="p", num_questions=1, source_files=None
            )

    def test_asset_priority_and_other_content_type(self) -> None:
        docstore = MagicMock()
        project = MagicMock()
        svc = self._svc(docstore, project)
        assets = [
            {"content_type": "image", "source_file": "z", "doc_id": "1"},
            {"content_type": "unknown", "source_file": "a", "doc_id": "2"},
            {"content_type": "table", "source_file": "a", "doc_id": "3"},
            {"content_type": "text", "source_file": "b", "doc_id": "4"},
        ]
        pri = [svc._asset_priority(a) for a in assets]
        self.assertEqual(
            sorted(range(len(assets)), key=lambda i: pri[i]),
            [3, 2, 0, 1],
        )

    def test_build_context_respects_max_chars(self) -> None:
        docstore = MagicMock()
        project = MagicMock()
        svc = self._svc(docstore, project)
        chunk = "x" * 1200
        raw_assets = [
            {
                "doc_id": f"d{i}",
                "content_type": "text",
                "source_file": "f.pdf",
                "metadata": {},
                "summary": "",
                "raw_content": chunk,
            }
            for i in range(30)
        ]
        ctx = svc._build_generation_context(raw_assets)
        self.assertLessEqual(len(ctx), MAX_CONTEXT_CHARS)
        self.assertGreater(len(ctx), 2000)

    def test_format_asset_block_other_type_uses_raw_preview_cap(self) -> None:
        docstore = MagicMock()
        project = MagicMock()
        svc = self._svc(docstore, project)
        block = svc._format_asset_block(
            {
                "content_type": "other",
                "source_file": "f.pdf",
                "doc_id": "d1",
                "metadata": {},
                "summary": "",
                "raw_content": "y" * 900,
            }
        )
        self.assertIn("content_preview", block)
        self.assertIn("y" * 800, block)

    def test_extract_json_array_missing_brackets(self) -> None:
        with self.assertRaisesRegex(ValueError, "JSON array"):
            extract_json_array("no brackets here")


if __name__ == "__main__":
    unittest.main()
