from __future__ import annotations

from src.domain.pipeline_latency import PipelineLatency
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


def test_to_row_evaluation_dict_serializes_pipeline_latency() -> None:
    lat = PipelineLatency(total_ms=99.0, answer_generation_ms=1.0)
    run = RagInspectAnswerRun(
        pipeline=None,
        answer="x",
        latency_ms=99.0,
        full_latency=lat,
    )
    assert run.to_row_evaluation_dict()["latency"] == lat.to_dict()
