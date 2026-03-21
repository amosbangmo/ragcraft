import unittest

from src.domain.source_citation import SourceCitation
from src.services.prompt_builder_service import PromptBuilderService


class TestPromptBuilderService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = PromptBuilderService(
            max_text_chars_per_asset=1000,
            max_table_chars_per_asset=1000,
        )

    def test_table_instruction_omitted_by_default(self) -> None:
        p = self.svc.build_prompt(
            question="What is X?",
            chat_history=[],
            raw_context="ctx",
        )
        self.assertNotIn("Table-focused question", p)

    def test_table_instruction_injected_when_provided(self) -> None:
        p = self.svc.build_prompt(
            question="Which row?",
            chat_history=[],
            raw_context="ctx",
            table_aware_instruction="Table-focused question: read carefully.",
        )
        self.assertIn("Table-focused question: read carefully.", p)
        self.assertIn("Raw multimodal context:", p)

    def test_table_asset_includes_structured_excerpt(self) -> None:
        asset = {
            "content_type": "table",
            "doc_id": "d1",
            "source_file": "f.pdf",
            "raw_content": "<table><tr><th>A</th></tr><tr><td>1</td></tr></table>",
            "summary": "s",
            "metadata": {
                "structured_table": {"headers": ["A"], "rows": [["1"]]},
                "table_text": "A\n1",
            },
        }
        cit = SourceCitation(
            source_number=1,
            doc_id="d1",
            source_file="f.pdf",
            content_type="table",
            page_label=None,
            locator_label=None,
            display_label="Source 1",
            prompt_label="[Source 1]",
            metadata={},
        )
        block = self.svc._format_raw_asset_for_prompt(asset=asset, citation=cit)
        self.assertIn("Structured table excerpt:", block)
        self.assertIn("Column headers:", block)
        self.assertIn("Raw table HTML:", block)

    def test_table_asset_fallback_when_no_structured_rows(self) -> None:
        asset = {
            "content_type": "table",
            "doc_id": "d1",
            "source_file": "f.pdf",
            "raw_content": "<table></table>",
            "summary": "s",
            "metadata": {"structured_table": {"headers": [], "rows": []}, "table_text": ""},
        }
        cit = SourceCitation(
            source_number=1,
            doc_id="d1",
            source_file="f.pdf",
            content_type="table",
            page_label=None,
            locator_label=None,
            display_label="Source 1",
            prompt_label="[Source 1]",
            metadata={},
        )
        block = self.svc._format_raw_asset_for_prompt(asset=asset, citation=cit)
        self.assertNotIn("Structured table excerpt:", block)
        self.assertIn("Raw table HTML:", block)


if __name__ == "__main__":
    unittest.main()
