from __future__ import annotations

from src.domain.rag_inspect_answer_run import RagInspectAnswerRun


def test_to_row_evaluation_dict_matches_benchmark_row_contract() -> None:
    run = RagInspectAnswerRun(
        pipeline=None,
        answer="a",
        latency_ms=12.0,
        full_latency=None,
    )
    d = run.to_row_evaluation_dict()
    assert d == {
        "pipeline": None,
        "answer": "a",
        "latency_ms": 12.0,
        "latency": None,
    }
