import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from src.services.semantic_similarity_service import SemanticSimilarityService


class TestSemanticSimilarityService(unittest.TestCase):
    def test_empty_or_one_side_returns_zero(self) -> None:
        svc = SemanticSimilarityService()
        self.assertEqual(svc.compute_similarity("", "b"), 0.0)
        self.assertEqual(svc.compute_similarity("a", ""), 0.0)
        self.assertEqual(svc.compute_similarity("  ", "x"), 0.0)

    def test_identical_strings(self) -> None:
        svc = SemanticSimilarityService()
        self.assertEqual(svc.compute_similarity("same", "same"), 1.0)

    @patch("sentence_transformers.SentenceTransformer")
    def test_encode_cosine_path(self, mock_st_cls) -> None:
        mock_model = MagicMock()
        emb = np.array([[1.0, 0.0], [1.0, 0.0]], dtype=float)
        mock_model.encode.return_value = emb
        mock_st_cls.return_value = mock_model

        svc = SemanticSimilarityService(model_name="dummy")
        score = svc.compute_similarity("hello there", "hello again")
        self.assertAlmostEqual(score, 1.0, places=5)
        mock_model.encode.assert_called()

    @patch("sentence_transformers.SentenceTransformer")
    def test_encode_failure_returns_zero(self, mock_st_cls) -> None:
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("boom")
        mock_st_cls.return_value = mock_model

        svc = SemanticSimilarityService(model_name="dummy")
        self.assertEqual(svc.compute_similarity("a", "b"), 0.0)


if __name__ == "__main__":
    unittest.main()
