import unittest

from src.infrastructure.adapters.rag.prompt_source_service import PromptSourceService


class TestPromptSourceService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = PromptSourceService()

    def test_section_and_page_in_prompt_label(self) -> None:
        assets = [
            {
                "doc_id": "a",
                "source_file": "doc.pdf",
                "content_type": "text",
                "metadata": {
                    "page_number": 2,
                    "chunk_title": "Introduction",
                    "start_element_index": 1,
                    "end_element_index": 1,
                },
            }
        ]
        sources = self.svc.build_prompt_sources(assets)
        self.assertEqual(len(sources), 1)
        self.assertIn("Section: Introduction", sources[0].display_label)
        self.assertIn("[Section: Introduction]", sources[0].prompt_label)
        self.assertIn("[Page 2]", sources[0].prompt_label)
        self.assertIn("[Element 1]", sources[0].prompt_label)

    def test_no_section_unchanged_shape(self) -> None:
        assets = [
            {
                "doc_id": "a",
                "source_file": "doc.pdf",
                "content_type": "text",
                "metadata": {},
            }
        ]
        sources = self.svc.build_prompt_sources(assets)
        self.assertEqual(sources[0].prompt_label, "[Source 1]")


if __name__ == "__main__":
    unittest.main()
