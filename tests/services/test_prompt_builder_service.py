import unittest

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


if __name__ == "__main__":
    unittest.main()
