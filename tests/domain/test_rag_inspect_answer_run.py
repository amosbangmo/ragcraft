from __future__ import annotations

from src.domain.evaluation.gold_qa_row_input import GoldQaPipelineRowInput
from src.domain.pipeline_latency import PipelineLatency
from src.domain.rag_inspect_answer_run import RagInspectAnswerRun


def test_as_row_evaluation_input_matches_gold_qa_row_contract() -> None:
    run = RagInspectAnswerRun(
        pipeline=None,
        answer="a",
        latency_ms=12.0,
        full_latency=None,
    )
    row = run.as_row_evaluation_input()
    assert isinstance(row, GoldQaPipelineRowInput)
    assert row.pipeline is None
    assert row.answer == "a"
    assert row.latency_ms == 12.0
    assert row.full_latency is None


def test_as_row_evaluation_input_carries_pipeline_latency() -> None:
    lat = PipelineLatency(total_ms=99.0, answer_generation_ms=1.0)
    run = RagInspectAnswerRun(
        pipeline=None,
        answer="x",
        latency_ms=99.0,
        full_latency=lat,
    )
    row = run.as_row_evaluation_input()
    assert row.full_latency == lat
