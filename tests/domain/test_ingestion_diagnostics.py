import unittest

from src.domain.ingestion_diagnostics import IngestionDiagnostics


class TestIngestionDiagnostics(unittest.TestCase):
    def test_to_dict_structure(self):
        d = IngestionDiagnostics(
            extraction_ms=1.0,
            summarization_ms=2.0,
            indexing_ms=3.0,
            total_ms=6.0,
            extracted_elements=4,
            generated_assets=4,
            errors=["a"],
        ).to_dict()

        self.assertEqual(d["extraction_ms"], 1.0)
        self.assertEqual(d["summarization_ms"], 2.0)
        self.assertEqual(d["indexing_ms"], 3.0)
        self.assertEqual(d["total_ms"], 6.0)
        self.assertEqual(d["extracted_elements"], 4)
        self.assertEqual(d["generated_assets"], 4)
        self.assertEqual(d["errors"], ["a"])

    def test_to_dict_normalizes_none_errors(self):
        d = IngestionDiagnostics().to_dict()
        self.assertEqual(d["errors"], [])

    def test_defaults_non_negative(self):
        diag = IngestionDiagnostics()
        self.assertGreaterEqual(diag.extraction_ms, 0.0)
        self.assertGreaterEqual(diag.summarization_ms, 0.0)
        self.assertGreaterEqual(diag.indexing_ms, 0.0)
        self.assertGreaterEqual(diag.total_ms, 0.0)
        self.assertGreaterEqual(diag.extracted_elements, 0)
        self.assertGreaterEqual(diag.generated_assets, 0)


if __name__ == "__main__":
    unittest.main()
