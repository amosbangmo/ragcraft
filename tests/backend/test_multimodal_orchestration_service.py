import unittest

from src.backend.multimodal_orchestration_service import MultimodalOrchestrationService


class TestMultimodalOrchestrationService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = MultimodalOrchestrationService()

    def test_analyze_empty(self) -> None:
        a = self.svc.analyze([])
        self.assertFalse(a["has_text"])
        self.assertFalse(a["has_table"])
        self.assertFalse(a["has_image"])
        self.assertEqual(a["modality_count"], 0)

    def test_analyze_text_only(self) -> None:
        a = self.svc.analyze([{"content_type": "text"}])
        self.assertTrue(a["has_text"])
        self.assertFalse(a["has_table"])
        self.assertFalse(a["has_image"])
        self.assertEqual(a["modality_count"], 1)

    def test_analyze_mixed_case_content_type(self) -> None:
        a = self.svc.analyze([{"content_type": "TABLE"}, {"content_type": " Image "}])
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
                analysis = self.svc.analyze(assets)
                self.assertEqual(self.svc.build_prompt_hint(analysis), "")

    def test_hint_text_and_table(self) -> None:
        analysis = self.svc.analyze(
            [{"content_type": "text"}, {"content_type": "table"}]
        )
        hint = self.svc.build_prompt_hint(analysis)
        self.assertIn("table", hint.lower())
        self.assertIn("text", hint.lower())
        self.assertIn("bullet", hint.lower())

    def test_hint_all_three(self) -> None:
        analysis = self.svc.analyze(
            [
                {"content_type": "text"},
                {"content_type": "table"},
                {"content_type": "image"},
            ]
        )
        hint = self.svc.build_prompt_hint(analysis)
        self.assertIn("tables", hint.lower())
        self.assertIn("image", hint.lower())
