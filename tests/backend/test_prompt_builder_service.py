import unittest

from src.domain.prompt_source import PromptSource
from src.infrastructure.services.prompt_builder_service import PromptBuilderService


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
        self.assertNotIn("grouped by document layout", p)

    def test_table_instruction_injected_when_provided(self) -> None:
        p = self.svc.build_prompt(
            question="Which row?",
            chat_history=[],
            raw_context="ctx",
            table_aware_instruction="Table-focused question: read carefully.",
        )
        self.assertIn("Table-focused question: read carefully.", p)
        self.assertIn("Raw multimodal context:", p)

    def test_orchestration_hint_omitted_by_default(self) -> None:
        p = self.svc.build_prompt(
            question="Q?",
            chat_history=[],
            raw_context="ctx",
        )
        self.assertNotIn("Multimodal orchestration:", p)

    def test_orchestration_hint_injected_when_provided(self) -> None:
        p = self.svc.build_prompt(
            question="Q?",
            chat_history=[],
            raw_context="ctx",
            orchestration_hint="Use table for numbers.",
        )
        self.assertIn("Multimodal orchestration:", p)
        self.assertIn("Use table for numbers.", p)

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
        cit = PromptSource(
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
        block = self.svc._format_raw_asset_for_prompt(asset=asset, prompt_source=cit)
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
        cit = PromptSource(
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
        block = self.svc._format_raw_asset_for_prompt(asset=asset, prompt_source=cit)
        self.assertNotIn("Structured table excerpt:", block)
        self.assertIn("Raw table HTML:", block)

    def test_image_asset_includes_context_blocks(self) -> None:
        image = {
            "content_type": "image",
            "doc_id": "im1",
            "source_file": "r.pdf",
            "summary": "A diagram of the workflow.",
            "metadata": {
                "page_number": 3,
                "image_title": "Workflow diagram",
                "surrounding_text": "See the steps illustrated here.",
                "element_category": "Image",
            },
        }
        text_neighbor = {
            "content_type": "text",
            "doc_id": "tx1",
            "source_file": "r.pdf",
            "raw_content": "Step one loads configuration.",
            "metadata": {"page_start": 3, "page_end": 3, "source_file": "r.pdf"},
        }
        cit = PromptSource(
            source_number=1,
            doc_id="im1",
            source_file="r.pdf",
            content_type="image",
            page_label=None,
            locator_label=None,
            display_label="Source 1",
            prompt_label="[Source 1]",
            metadata={},
        )
        ctx_map, enriched = self.svc.prepare_image_contexts([image, text_neighbor])
        self.assertTrue(enriched)
        block = self.svc._format_raw_asset_for_prompt(
            asset=image,
            prompt_source=cit,
            image_context=ctx_map["im1"],
        )
        self.assertIn("Workflow diagram", block)
        self.assertIn("Page 3", block)
        self.assertIn("Same-page text excerpt", block)
        self.assertIn("Nearby retrieved text chunks", block)
        self.assertIn("Image retrieval summary:", block)
        self.assertIn("diagram of the workflow", block.lower())

    def test_image_fallback_without_precomputed_context(self) -> None:
        image = {
            "content_type": "image",
            "doc_id": "im2",
            "source_file": "r.pdf",
            "summary": "Summary only.",
            "metadata": {"image_title": "Fig A"},
        }
        cit = PromptSource(
            source_number=1,
            doc_id="im2",
            source_file="r.pdf",
            content_type="image",
            page_label=None,
            locator_label=None,
            display_label="Source 1",
            prompt_label="[Source 1]",
            metadata={},
        )
        block = self.svc._format_raw_asset_for_prompt(
            asset=image, prompt_source=cit, image_context=None
        )
        self.assertIn("Fig A", block)
        self.assertIn("Image retrieval summary:", block)
        self.assertIn("Summary only.", block)

    def test_grouped_raw_context_has_headers_and_type_tags(self) -> None:
        t = {
            "content_type": "text",
            "doc_id": "t1",
            "source_file": "f.pdf",
            "raw_content": "hello",
            "metadata": {"page_number": 2, "chunk_title": "Intro"},
        }
        tb = {
            "content_type": "table",
            "doc_id": "tb1",
            "source_file": "f.pdf",
            "raw_content": "<table></table>",
            "summary": "s",
            "metadata": {"table_text": ""},
        }
        c1 = PromptSource(
            source_number=1,
            doc_id="t1",
            source_file="f.pdf",
            content_type="text",
            page_label=None,
            locator_label=None,
            display_label="Source 1",
            prompt_label="[Source 1]",
            metadata={},
        )
        c2 = PromptSource(
            source_number=2,
            doc_id="tb1",
            source_file="f.pdf",
            content_type="table",
            page_label=None,
            locator_label=None,
            display_label="Source 2",
            prompt_label="[Source 2]",
            metadata={},
        )
        ctx = self.svc.build_raw_context(
            raw_assets=[t, tb],
            prompt_sources=[c1, c2],
            asset_groups=[[t, tb]],
        )
        self.assertIn("=== ", ctx)
        self.assertIn("Page 2", ctx)
        self.assertIn("[Text]", ctx)
        self.assertIn("[Table]", ctx)
        self.assertIn("Related assets", ctx)

    def test_layout_aware_prompt_adds_instructions(self) -> None:
        p = self.svc.build_prompt(
            question="Q?",
            chat_history=[],
            raw_context="=== Page 1 ===\n…",
            layout_aware=True,
        )
        self.assertIn("grouped by document layout", p)


if __name__ == "__main__":
    unittest.main()
