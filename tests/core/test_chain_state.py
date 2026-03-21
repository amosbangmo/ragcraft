import unittest
from unittest.mock import patch

from src.core.chain_state import (
    CHAIN_CACHE_KEY,
    get_cached_chain,
    invalidate_all_project_chains,
    invalidate_project_chain,
    set_cached_chain,
)


class TestChainState(unittest.TestCase):
    def _session(self) -> dict:
        return {}

    @patch("src.core.chain_state.st")
    def test_cache_roundtrip(self, mock_st) -> None:
        mock_st.session_state = self._session()
        set_cached_chain("k1", "chain-a")
        self.assertEqual(get_cached_chain("k1"), "chain-a")
        invalidate_project_chain("k1")
        self.assertIsNone(get_cached_chain("k1"))

    @patch("src.core.chain_state.st")
    def test_invalidate_all_when_present(self, mock_st) -> None:
        mock_st.session_state = {CHAIN_CACHE_KEY: {"a": 1, "b": 2}}
        invalidate_all_project_chains()
        self.assertEqual(mock_st.session_state[CHAIN_CACHE_KEY], {})

    @patch("src.core.chain_state.st")
    def test_invalidate_all_when_absent(self, mock_st) -> None:
        mock_st.session_state = {}
        invalidate_all_project_chains()


if __name__ == "__main__":
    unittest.main()
