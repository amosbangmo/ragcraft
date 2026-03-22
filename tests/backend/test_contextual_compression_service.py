import unittest

from src.infrastructure.services.contextual_compression_service import ContextualCompressionService


class TestContextualCompressionService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = ContextualCompressionService()

    def test_empty_assets_returns_empty(self) -> None:
        self.assertEqual(self.svc.compress(query="anything", assets=[]), [])

    def test_empty_query_does_not_strip_text(self) -> None:
        assets = [
            {
                "content_type": "text",
                "raw_content": "Alpha sentence. Beta sentence.",
                "metadata": {},
            }
        ]
        out = self.svc.compress(query="", assets=assets)
        self.assertEqual(out[0]["raw_content"], assets[0]["raw_content"])

    def test_keeps_overlapping_sentences_only(self) -> None:
        assets = [
            {
                "content_type": "text",
                "raw_content": "Unrelated line. Python is great for data work. Another unrelated line.",
                "metadata": {},
            }
        ]
        out = self.svc.compress(query="Tell me about Python", assets=assets)
        self.assertIn("Python", out[0]["raw_content"])
        self.assertNotIn("Unrelated", out[0]["raw_content"])

    def test_reduces_prompt_char_estimate(self) -> None:
        long_text = "Foo bar. " * 50 + "Target keyword here. " + "Baz qux. " * 50
        assets = [{"content_type": "text", "raw_content": long_text, "metadata": {}}]
        before = self.svc.prompt_char_estimate(assets)
        out = self.svc.compress(query="keyword", assets=assets)
        after = self.svc.prompt_char_estimate(out)
        self.assertLess(after, before)

    def test_table_unchanged(self) -> None:
        assets = [
            {
                "content_type": "table",
                "raw_content": "<table><tr><td>x</td></tr></table>",
                "metadata": {"table_text": "x"},
            }
        ]
        out = self.svc.compress(query="nothing", assets=assets)
        self.assertEqual(out[0]["raw_content"], assets[0]["raw_content"])

    def test_image_clears_raw_content(self) -> None:
        assets = [
            {
                "content_type": "image",
                "raw_content": "huge-base64-payload",
                "summary": "A chart showing sales.",
                "metadata": {},
            }
        ]
        out = self.svc.compress(query="sales", assets=assets)
        self.assertEqual(out[0]["raw_content"], "")
        self.assertEqual(out[0]["summary"], assets[0]["summary"])
        # Prompt estimate is summary-only for images (binary omitted from prompt either way).
        self.assertEqual(
            self.svc.prompt_char_estimate(out),
            self.svc.prompt_char_estimate(assets),
        )
