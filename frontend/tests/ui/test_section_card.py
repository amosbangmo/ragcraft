import unittest
from unittest.mock import patch

from components.shared.section_card import inject_section_card_styles, section_card


class TestSectionCard(unittest.TestCase):
    @patch("components.shared.section_card.st")
    def test_inject_styles_calls_markdown(self, mock_st) -> None:
        inject_section_card_styles()
        mock_st.markdown.assert_called()
        call_kw = mock_st.markdown.call_args.kwargs
        self.assertTrue(call_kw.get("unsafe_allow_html"))

    @patch("components.shared.section_card.st")
    def test_section_card_context_and_danger(self, mock_st) -> None:
        with section_card("T", "S", min_height=100, danger=True):
            pass
        self.assertGreaterEqual(mock_st.markdown.call_count, 2)


if __name__ == "__main__":
    unittest.main()
