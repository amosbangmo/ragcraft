import unittest

from src.infrastructure.adapters.rag.image_context_service import ImageContextService


class TestImageContextService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = ImageContextService()

    def test_build_context_combines_metadata_and_neighbors(self) -> None:
        asset = {
            "content_type": "image",
            "doc_id": "img1",
            "source_file": "a.pdf",
            "metadata": {
                "page_number": 2,
                "image_title": "Figure 1: Revenue",
                "surrounding_text": "The chart below shows quarterly results.",
            },
        }
        neighbors = [
            {
                "content_type": "text",
                "raw_content": "Q3 revenue exceeded expectations due to enterprise sales.",
                "summary": "s",
                "metadata": {"page_start": 2, "page_end": 2, "source_file": "a.pdf"},
            }
        ]
        ctx = self.svc.build_context(asset, neighbors)
        self.assertEqual(ctx["image_title"], "Figure 1: Revenue")
        self.assertEqual(ctx["page_context"], "Page 2")
        self.assertIn("revenue", (ctx["neighbor_text"] or "").lower())
        self.assertIn("surrounding", (ctx["contextual_summary"] or "").lower())
        self.assertTrue(self.svc.is_context_enriched(ctx))

    def test_is_context_enriched_false_when_only_title(self) -> None:
        asset = {
            "content_type": "image",
            "metadata": {"image_title": "Fig 2", "page_number": 1},
        }
        ctx = self.svc.build_context(asset, [])
        self.assertFalse(self.svc.is_context_enriched(ctx))

    def test_find_text_neighbors_respects_page_overlap(self) -> None:
        image = {
            "content_type": "image",
            "doc_id": "i1",
            "source_file": "f.pdf",
            "metadata": {"page_number": 5, "source_file": "f.pdf"},
        }
        pool = [
            image,
            {
                "content_type": "text",
                "doc_id": "t1",
                "source_file": "f.pdf",
                "raw_content": "on page five",
                "metadata": {"page_start": 5, "page_end": 5, "source_file": "f.pdf"},
            },
            {
                "content_type": "text",
                "doc_id": "t2",
                "source_file": "f.pdf",
                "raw_content": "other page",
                "metadata": {"page_start": 99, "page_end": 99, "source_file": "f.pdf"},
            },
        ]
        n = self.svc.find_text_neighbors(image, pool)
        self.assertEqual(len(n), 1)
        self.assertEqual(n[0].get("doc_id"), "t1")

    def test_find_text_neighbors_same_file_without_image_page(self) -> None:
        image = {
            "content_type": "image",
            "doc_id": "i1",
            "source_file": "x.docx",
            "metadata": {"source_file": "x.docx"},
        }
        pool = [
            image,
            {
                "content_type": "text",
                "doc_id": "t1",
                "source_file": "x.docx",
                "raw_content": "body text",
                "metadata": {"source_file": "x.docx"},
            },
        ]
        n = self.svc.find_text_neighbors(image, pool)
        self.assertEqual(len(n), 1)


if __name__ == "__main__":
    unittest.main()
