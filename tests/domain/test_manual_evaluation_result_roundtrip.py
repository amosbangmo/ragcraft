"""JSON round-trip for manual eval pipeline signals (stage_latency as PipelineLatency)."""

from __future__ import annotations

from src.domain.manual_evaluation_result import (
    ManualEvaluationPipelineSignals,
    manual_evaluation_result_from_plain_dict,
)
from src.domain.pipeline_latency import PipelineLatency


def test_manual_evaluation_result_from_plain_dict_parses_stage_latency() -> None:
    d = {
        "question": "q",
        "answer": "a",
        "expected_answer": None,
        "confidence": 0.5,
        "pipeline_signals": {
            "confidence": 0.5,
            "retrieval_mode": "faiss",
            "query_rewrite_enabled": True,
            "hybrid_retrieval_enabled": False,
            "latency_ms": 10.0,
            "stage_latency": {"query_rewrite_ms": 1.0, "total_ms": 10.0},
        },
    }
    r = manual_evaluation_result_from_plain_dict(d)
    assert r.pipeline_signals is not None
    assert isinstance(r.pipeline_signals, ManualEvaluationPipelineSignals)
    assert isinstance(r.pipeline_signals.stage_latency, PipelineLatency)
    assert r.pipeline_signals.stage_latency.query_rewrite_ms == 1.0
    assert r.pipeline_signals.stage_latency.total_ms == 10.0
