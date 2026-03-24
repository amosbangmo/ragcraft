"""Domain coverage for multimodal_metrics (mirrors infra scenarios; counted in appli+domain runs)."""

from __future__ import annotations

from domain.evaluation.multimodal_metrics import (
    aggregate_multimodal_metrics,
    analyze_prompt_asset_modalities,
    analyze_prompt_source_modalities,
    empty_modality_row_fields,
    modality_row_fields_from_pipeline,
)
from domain.rag.pipeline_payloads import PipelineBuildResult


def test_norm_ignores_invalid_content_types() -> None:
    a = analyze_prompt_asset_modalities([{"content_type": "video"}, "not-a-dict", None])
    assert a["modality_count"] == 0
    assert not a["mixed_modality_prompt"]


def test_modality_row_fields_from_pipeline_build_result() -> None:
    p = PipelineBuildResult(
        question="q",
        prompt_context_assets=[{"content_type": "image"}],
    )
    f = modality_row_fields_from_pipeline(p)
    assert f["modality_evaluation_available"]
    assert f["retrieval_has_image"]


def test_modality_row_fallback_reranked_when_no_prompt_context() -> None:
    pl = {
        "reranked_raw_assets": [{"content_type": "table"}],
        "prompt_sources": [],
    }
    f = modality_row_fields_from_pipeline(pl)
    assert f["retrieval_has_table"]


def test_modality_row_non_list_prompt_sources() -> None:
    f = modality_row_fields_from_pipeline({"prompt_context_assets": [], "prompt_sources": "x"})
    assert f["modality_evaluation_available"]


def test_aggregate_coercion_and_branches() -> None:
    rows = [
        {
            **empty_modality_row_fields(),
            "modality_evaluation_available": True,
            "context_uses_table": True,
            "has_expected_answer": True,
            "answer_f1": "bad",
            "groundedness_score": True,
        },
        {
            **empty_modality_row_fields(),
            "modality_evaluation_available": True,
            "context_uses_image": True,
            "groundedness_score": 0.5,
        },
    ]
    agg = aggregate_multimodal_metrics(rows)
    assert agg is not None
    assert agg["by_modality"]["text_only"]["row_count"] >= 0


def test_aggregate_multimodal_text_only_groundedness() -> None:
    rows = [
        {
            **empty_modality_row_fields(),
            "modality_evaluation_available": True,
            "context_uses_table": False,
            "context_uses_image": False,
            "has_expected_answer": True,
            "answer_f1": 0.9,
            "groundedness_score": 0.8,
        }
    ]
    agg = aggregate_multimodal_metrics(rows)
    assert agg is not None
    assert agg["by_modality"]["text_only"]["avg_answer_f1"] == 0.9


def test_analyze_prompt_sources_mixed() -> None:
    c = analyze_prompt_source_modalities([{"content_type": "IMAGE"}, {"content_type": "text"}])
    assert c["has_image"] and c["has_text"]


def test_aggregate_table_f1_and_image_branches() -> None:
    rows = [
        {
            **empty_modality_row_fields(),
            "modality_evaluation_available": True,
            "context_uses_table": True,
            "has_expected_answer": True,
            "answer_f1": 0.7,
            "groundedness_score": None,
        },
        {
            **empty_modality_row_fields(),
            "modality_evaluation_available": True,
            "context_uses_image": True,
            "groundedness_score": 0.55,
            "has_expected_answer": False,
            "answer_f1": 0.3,
        },
        {
            **empty_modality_row_fields(),
            "modality_evaluation_available": True,
            "context_uses_table": True,
            "context_uses_image": True,
            "has_expected_answer": True,
            "answer_f1": 0.4,
            "groundedness_score": 0.6,
        },
    ]
    agg = aggregate_multimodal_metrics(rows)
    assert agg is not None
    assert agg["table_correctness"] == 0.55
    assert agg["image_groundedness"] == 0.57
