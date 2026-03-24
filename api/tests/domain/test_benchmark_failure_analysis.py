from __future__ import annotations

from domain.evaluation.benchmark_failure_analysis import (
    FailureAnalysisService,
    _coerce_bool,
    _coerce_float,
    _coerce_int,
)


def test_coerce_helpers() -> None:
    assert _coerce_float("1.5") == 1.5
    assert _coerce_float(True) is None
    assert _coerce_bool("yes") is True
    assert _coerce_bool("no") is False
    assert _coerce_bool("maybe") is None
    assert _coerce_int(True) == 1
    assert _coerce_int("x") is None


def test_analyze_pipeline_failed_row() -> None:
    svc = FailureAnalysisService(top_examples_per_type=2)
    out = svc.analyze([{"pipeline_failed": True, "entry_id": 1}])
    assert out["failed_row_count"] == 0


def test_analyze_retrieval_failure_modes() -> None:
    svc = FailureAnalysisService()
    rows = [
        {
            "entry_id": 1,
            "retrieval_mode": "none",
        },
        {
            "entry_id": 2,
            "expected_doc_ids_count": 2,
            "recall_at_k": 0.1,
        },
    ]
    out = svc.analyze(rows)
    assert out["counts"].get("retrieval_failure", 0) >= 1


def test_analyze_grounding_and_citation() -> None:
    svc = FailureAnalysisService()
    rows = [
        {
            "entry_id": 1,
            "judge_failed": False,
            "groundedness_score": 0.1,
            "expected_doc_ids_count": 1,
            "prompt_doc_id_precision": 0.1,
            "citation_doc_id_recall": 0.1,
        }
    ]
    out = svc.analyze(rows)
    labels = out["row_failures"][0]["failure_labels"]
    assert "grounding_failure" in labels or "context_selection_failure" in labels


def test_analyze_hallucination_and_relevance() -> None:
    svc = FailureAnalysisService()
    rows = [
        {
            "entry_id": 1,
            "judge_failed": False,
            "hallucination_score": 0.1,
            "answer_relevance_score": 0.1,
            "confidence": 0.1,
        }
    ]
    out = svc.analyze(rows)
    assert out["row_failures"][0]["failure_labels"]


def test_analyze_table_misuse_and_image_hallucination() -> None:
    svc = FailureAnalysisService()
    rows = [
        {
            "entry_id": 1,
            "has_expected_answer": True,
            "context_uses_table": True,
            "answer_f1": 0.1,
            "groundedness_score": 0.9,
        },
        {
            "entry_id": 2,
            "judge_failed": False,
            "context_uses_image": True,
            "hallucination_score": 0.1,
        },
    ]
    out = svc.analyze(rows)
    all_labels = [lb for rf in out["row_failures"] for lb in rf["failure_labels"]]
    assert "table_misuse" in all_labels
    assert "image_hallucination" in all_labels


def test_analyze_judge_failure() -> None:
    svc = FailureAnalysisService()
    out = svc.analyze([{"entry_id": 1, "judge_failed": True}])
    assert "judge_failure" in out["row_failures"][0]["failure_labels"]


def test_analyze_critical_row() -> None:
    svc = FailureAnalysisService()
    out = svc.analyze(
        [
            {
                "entry_id": 1,
                "has_expected_answer": True,
                "answer_f1": 0.1,
                "confidence": 0.99,
            }
        ]
    )
    assert out["critical_count"] >= 1
    assert out["row_failures"][0]["failure_critical"] is True


def test_top_examples_zero() -> None:
    svc = FailureAnalysisService(top_examples_per_type=0)
    out = svc.analyze([{"entry_id": 1, "retrieval_mode": "none"}])
    assert out["examples"] == {}
