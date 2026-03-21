import unittest

from src.services.source_citation_service import SourceCitationService


class TestSourceCitationService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = SourceCitationService()

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
        cites = self.svc.build_citations(assets)
        self.assertEqual(len(cites), 1)
        self.assertIn("Section: Introduction", cites[0].display_label)
        self.assertIn("[Section: Introduction]", cites[0].prompt_label)
        self.assertIn("[Page 2]", cites[0].prompt_label)
        self.assertIn("[Element 1]", cites[0].prompt_label)

    def test_no_section_unchanged_shape(self) -> None:
        assets = [
            {
                "doc_id": "a",
                "source_file": "doc.pdf",
                "content_type": "text",
                "metadata": {},
            }
        ]
        cites = self.svc.build_citations(assets)
        self.assertEqual(cites[0].prompt_label, "[Source 1]")


if __name__ == "__main__":
    unittest.main()
