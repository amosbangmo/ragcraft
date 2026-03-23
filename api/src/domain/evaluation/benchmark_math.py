"""Deterministic rounding and summary helpers for benchmark payloads."""

from __future__ import annotations

import numpy as np

from domain.rag.pipeline_latency import PipelineLatency


def latency_stage_row_fields(latency: PipelineLatency | None) -> dict[str, float]:
    lat = latency or PipelineLatency()
    d = lat.to_dict()
    return {
        "query_rewrite_ms": round(float(d["query_rewrite_ms"]), 2),
        "retrieval_ms": round(float(d["retrieval_ms"]), 2),
        "reranking_ms": round(float(d["reranking_ms"]), 2),
        "prompt_build_ms": round(float(d["prompt_build_ms"]), 2),
        "answer_generation_ms": round(float(d["answer_generation_ms"]), 2),
    }


def r2(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def mean_round(values: list[float], ndigits: int) -> float | None:
    if not values:
        return None
    return round(float(np.mean(values)), ndigits)


def rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(float(numerator) / float(denominator), 2)
