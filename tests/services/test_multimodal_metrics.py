import unittest

from src.domain.multimodal_metrics import (
    aggregate_multimodal_metrics,
    analyze_citation_modalities,
    analyze_prompt_asset_modalities,
    empty_modality_row_fields,
    modality_row_fields_from_pipeline,
)


class TestMultimodalMetrics(unittest.TestCase):
    def test_analyze_prompt_detects_table_and_image(self) -> None:
        assets = [
            {"content_type": "text", "doc_id": "a1"},
            {"content_type": "table", "doc_id": "a2"},
            {"content_type": "image", "doc_id": "a3"},
        ]
        a = analyze_prompt_asset_modalities(assets)
        self.assertTrue(a["has_text"])
        self.assertTrue(a["has_table"])
        self.assertTrue(a["has_image"])
        self.assertEqual(a["modality_count"], 3)
        self.assertTrue(a["mixed_modality_prompt"])

    def test_analyze_citations(self) -> None:
        refs = [{"content_type": "table"}, {"doc_id": "x"}]
        c = analyze_citation_modalities(refs)
        self.assertTrue(c["has_table"])
        self.assertFalse(c["has_image"])

    def test_modality_row_fields_from_pipeline_prefers_prompt_context_assets(self) -> None:
        pl = {
            "prompt_context_assets": [
                {"content_type": "text"},
                {"content_type": "table"},
            ],
            "reranked_raw_assets": [{"content_type": "image"}],
            "source_references": [{"content_type": "image"}],
        }
        f = modality_row_fields_from_pipeline(pl)
        self.assertTrue(f["modality_evaluation_available"])
        self.assertTrue(f["retrieval_has_table"])
        self.assertFalse(f["retrieval_has_image"])
        self.assertTrue(f["context_uses_table"])
        self.assertTrue(f["context_uses_image"])
        self.assertTrue(f["mixed_modality_prompt"])

    def test_aggregate_requires_eligible_rows(self) -> None:
        self.assertIsNone(aggregate_multimodal_metrics([{"answer_f1": 1.0}]))
        rows = [
            {
                **empty_modality_row_fields(),
                "modality_evaluation_available": True,
                "context_uses_table": True,
                "context_uses_image": False,
                "mixed_modality_prompt": False,
                "has_expected_answer": True,
                "answer_f1": 0.8,
                "groundedness": 0.9,
            },
            {
                **empty_modality_row_fields(),
                "modality_evaluation_available": True,
                "context_uses_table": False,
                "context_uses_image": True,
                "mixed_modality_prompt": True,
                "has_expected_answer": True,
                "answer_f1": 0.5,
                "groundedness": 0.4,
            },
        ]
        agg = aggregate_multimodal_metrics(rows)
        assert agg is not None
        self.assertTrue(agg["has_multimodal_assets"])
        self.assertEqual(agg["eligible_rows"], 2)
        self.assertEqual(agg["table_usage_rate"], 0.5)
        self.assertEqual(agg["image_usage_rate"], 0.5)
        self.assertEqual(agg["multimodal_answers_rate"], 0.5)
        self.assertEqual(agg["table_correctness"], 0.8)
        self.assertEqual(agg["image_groundedness"], 0.4)


if __name__ == "__main__":
    unittest.main()
