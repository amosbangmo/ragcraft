import unittest

from src.application.chat.multimodal_prompt_hints import MultimodalPromptHints


class TestMultimodalPromptHints(unittest.TestCase):
    def setUp(self) -> None:
        self.hints = MultimodalPromptHints()

    def test_analyze_modalities_empty(self) -> None:
        a = self.hints.analyze_modalities([])
        self.assertFalse(a["has_text"])
        self.assertFalse(a["has_table"])
        self.assertFalse(a["has_image"])
        self.assertEqual(a["modality_count"], 0)

    def test_analyze_modalities_text_only(self) -> None:
        a = self.hints.analyze_modalities([{"content_type": "text"}])
        self.assertTrue(a["has_text"])
        self.assertFalse(a["has_table"])
        self.assertFalse(a["has_image"])
        self.assertEqual(a["modality_count"], 1)

    def test_analyze_modalities_mixed_case_content_type(self) -> None:
        a = self.hints.analyze_modalities([{"content_type": "TABLE"}, {"content_type": " Image "}])
        self.assertFalse(a["has_text"])
        self.assertTrue(a["has_table"])
        self.assertTrue(a["has_image"])
        self.assertEqual(a["modality_count"], 2)

    def test_hint_empty_for_single_modality(self) -> None:
        for assets in (
            [{"content_type": "text"}],
            [{"content_type": "table"}],
            [{"content_type": "image"}],
        ):
            with self.subTest(assets=assets):
                analysis = self.hints.analyze_modalities(assets)
                self.assertEqual(self.hints.build_multimodal_prompt_hint(analysis), "")

    def test_hint_text_and_table(self) -> None:
        analysis = self.hints.analyze_modalities(
            [{"content_type": "text"}, {"content_type": "table"}]
        )
        hint = self.hints.build_multimodal_prompt_hint(analysis)
        self.assertIn("table", hint.lower())
        self.assertIn("text", hint.lower())
        self.assertIn("bullet", hint.lower())

    def test_hint_all_three(self) -> None:
        analysis = self.hints.analyze_modalities(
            [
                {"content_type": "text"},
                {"content_type": "table"},
                {"content_type": "image"},
            ]
        )
        hint = self.hints.build_multimodal_prompt_hint(analysis)
        self.assertIn("tables", hint.lower())
        self.assertIn("image", hint.lower())
