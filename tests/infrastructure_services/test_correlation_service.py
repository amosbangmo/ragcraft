import unittest

from src.infrastructure.services.correlation_service import CorrelationService


class TestCorrelationService(unittest.TestCase):
    def test_empty_rows(self) -> None:
        out = CorrelationService().compute([])
        self.assertFalse(out["available"])
        self.assertEqual(out["reason"], "no_rows")

    def test_perfect_linear_pair(self) -> None:
        rows = [
            {
                "confidence": 0.1,
                "answer_f1": 1.0,
                "groundedness_score": 0.5,
                "prompt_doc_id_precision": 0.0,
                "prompt_doc_id_recall": 0.0,
                "latency_ms": 10.0,
            },
            {
                "confidence": 0.2,
                "answer_f1": 2.0,
                "groundedness_score": 0.6,
                "prompt_doc_id_precision": 0.1,
                "prompt_doc_id_recall": 0.1,
                "latency_ms": 20.0,
            },
            {
                "confidence": 0.3,
                "answer_f1": 3.0,
                "groundedness_score": 0.7,
                "prompt_doc_id_precision": 0.2,
                "prompt_doc_id_recall": 0.2,
                "latency_ms": 30.0,
            },
        ]
        out = CorrelationService().compute(rows)
        self.assertTrue(out["available"])
        r = out["pairwise"].get("confidence_vs_answer_f1")
        self.assertIsNotNone(r)
        self.assertAlmostEqual(float(r), 1.0, places=5)

    def test_constant_column_yields_no_finite_pair(self) -> None:
        rows = [
            {
                "confidence": 0.1,
                "answer_f1": 0.5,
                "groundedness_score": 0.5,
                "prompt_doc_id_precision": 0.0,
                "prompt_doc_id_recall": 0.0,
                "latency_ms": 10.0,
            },
            {
                "confidence": 0.9,
                "answer_f1": 0.5,
                "groundedness_score": 0.6,
                "prompt_doc_id_precision": 0.1,
                "prompt_doc_id_recall": 0.1,
                "latency_ms": 20.0,
            },
        ]
        out = CorrelationService().compute(rows)
        self.assertTrue(out["available"])
        self.assertIsNone(out["pairwise"].get("confidence_vs_answer_f1"))

    def test_insufficient_metrics_when_only_one_series(self) -> None:
        rows = [{"confidence": 0.1}, {"confidence": 0.2}]
        out = CorrelationService().compute(rows)
        self.assertFalse(out["available"])
        self.assertEqual(out["reason"], "insufficient_metrics")


if __name__ == "__main__":
    unittest.main()
