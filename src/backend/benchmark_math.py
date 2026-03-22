"""Deterministic rounding and summary helpers for benchmark payloads."""

from __future__ import annotations

import numpy as np


def latency_stage_row_fields(latency: dict | None) -> dict[str, float]:
    if not latency:
        return {
            "query_rewrite_ms": 0.0,
            "retrieval_ms": 0.0,
            "reranking_ms": 0.0,
            "prompt_build_ms": 0.0,
            "answer_generation_ms": 0.0,
        }
    return {
        "query_rewrite_ms": round(float(latency.get("query_rewrite_ms", 0.0)), 2),
        "retrieval_ms": round(float(latency.get("retrieval_ms", 0.0)), 2),
        "reranking_ms": round(float(latency.get("reranking_ms", 0.0)), 2),
        "prompt_build_ms": round(float(latency.get("prompt_build_ms", 0.0)), 2),
        "answer_generation_ms": round(float(latency.get("answer_generation_ms", 0.0)), 2),
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
