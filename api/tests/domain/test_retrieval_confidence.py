from __future__ import annotations

from domain.rag.retrieval.retrieval_confidence import compute_confidence_from_reranked_assets


def test_empty_assets_returns_zero() -> None:
    assert compute_confidence_from_reranked_assets(reranked_raw_assets=[]) == 0.0


def test_single_score() -> None:
    v = compute_confidence_from_reranked_assets(
        reranked_raw_assets=[{"metadata": {"rerank_score": 1.0}}]
    )
    assert 0.0 <= v <= 1.0


def test_two_scores_gap_branch() -> None:
    v = compute_confidence_from_reranked_assets(
        reranked_raw_assets=[
            {"metadata": {"rerank_score": 5.0}},
            {"metadata": {"rerank_score": 0.0}},
        ]
    )
    assert v > 0


def test_negative_score_sigmoid_branch() -> None:
    v = compute_confidence_from_reranked_assets(
        reranked_raw_assets=[{"metadata": {"rerank_score": -2.0}}]
    )
    assert 0.0 <= v <= 1.0


def test_skip_non_numeric_rerank() -> None:
    v = compute_confidence_from_reranked_assets(
        reranked_raw_assets=[
            {"metadata": {"rerank_score": "x"}},
            {"metadata": {"rerank_score": 0.5}},
        ]
    )
    assert v >= 0


def test_metadata_not_dict() -> None:
    v = compute_confidence_from_reranked_assets(
        reranked_raw_assets=[{"metadata": "nope"}, {"metadata": {"rerank_score": 1.0}}]
    )
    assert v > 0


def test_source_diversity_unlabeled() -> None:
    v = compute_confidence_from_reranked_assets(
        reranked_raw_assets=[
            {"metadata": {"rerank_score": 1.0, "source_file": ""}},
            {"metadata": {"rerank_score": 0.5, "source_file": None}},
        ]
    )
    assert 0.0 <= v <= 1.0


def test_source_diversity_labeled() -> None:
    v = compute_confidence_from_reranked_assets(
        reranked_raw_assets=[
            {"metadata": {"rerank_score": 1.0, "source_file": "a.pdf"}},
            {"metadata": {"rerank_score": 0.5, "source_file": "b.pdf"}},
        ]
    )
    assert v > 0


def test_source_diversity_same_file_twice() -> None:
    v = compute_confidence_from_reranked_assets(
        reranked_raw_assets=[
            {"metadata": {"rerank_score": 1.0, "source_file": "same.pdf"}},
            {"metadata": {"rerank_score": 0.5, "source_file": "same.pdf"}},
        ]
    )
    assert 0.0 <= v <= 1.0
