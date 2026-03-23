import unittest

from infrastructure.evaluation.evaluation_service import EvaluationService


class TestEvaluationNDCG(unittest.TestCase):
    def test_ndcg_empty_ranked(self) -> None:
        ev = EvaluationService.__new__(EvaluationService)
        self.assertEqual(
            ev._compute_ndcg_at_k(ranked_doc_ids=[], expected_doc_ids={"a"}),
            0.0,
        )

    def test_ndcg_no_expected(self) -> None:
        ev = EvaluationService.__new__(EvaluationService)
        self.assertEqual(
            ev._compute_ndcg_at_k(ranked_doc_ids=["a", "b"], expected_doc_ids=set()),
            0.0,
        )

    def test_ndcg_perfect_ordering(self) -> None:
        ev = EvaluationService.__new__(EvaluationService)
        n = ev._compute_ndcg_at_k(
            ranked_doc_ids=["a", "b", "c"],
            expected_doc_ids={"a", "b"},
        )
        self.assertAlmostEqual(n, 1.0, places=5)

    def test_ndcg_relevant_later_is_below_one(self) -> None:
        ev = EvaluationService.__new__(EvaluationService)
        perfect = ev._compute_ndcg_at_k(
            ranked_doc_ids=["a", "b"],
            expected_doc_ids={"a"},
        )
        worse = ev._compute_ndcg_at_k(
            ranked_doc_ids=["b", "a"],
            expected_doc_ids={"a"},
        )
        self.assertAlmostEqual(perfect, 1.0, places=5)
        self.assertLess(worse, perfect)
        self.assertGreater(worse, 0.0)


if __name__ == "__main__":
    unittest.main()
