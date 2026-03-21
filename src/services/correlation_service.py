from __future__ import annotations

from typing import Any

import numpy as np

# Logical metric name -> row payload key (evaluation row ``data``).
CORRELATION_METRIC_KEYS: tuple[tuple[str, str], ...] = (
    ("confidence", "confidence"),
    ("answer_correctness", "answer_f1"),
    ("groundedness_score", "groundedness_score"),
    ("prompt_source_precision", "prompt_source_precision"),
    ("prompt_source_recall", "prompt_source_recall"),
    ("latency_ms", "latency_ms"),
)

_STRONG_THRESHOLD = 0.6


def _as_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pearson_pair(x: np.ndarray, y: np.ndarray) -> float | None:
    mask = np.isfinite(x) & np.isfinite(y)
    n = int(mask.sum())
    if n < 2:
        return None
    a = x[mask]
    b = y[mask]
    if float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
        return None
    r = float(np.corrcoef(a, b)[0, 1])
    if not np.isfinite(r):
        return None
    return r


class CorrelationService:
    """
    Pearson correlations between core evaluation metrics on per-entry rows.

    Skips gracefully when columns are missing, constant, or there are too few points.
    """

    def compute(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {
                "available": False,
                "reason": "no_rows",
                "metrics_used": [],
                "sample_size": 0,
                "matrix": {},
                "pairwise": {},
                "highlights": {"strong_positive": [], "strong_negative": []},
                "strong_threshold": _STRONG_THRESHOLD,
            }

        logical_names: list[str] = []
        row_keys: list[str] = []
        for logical, rkey in CORRELATION_METRIC_KEYS:
            if any(_as_float(r.get(rkey)) is not None for r in rows):
                logical_names.append(logical)
                row_keys.append(rkey)

        if len(logical_names) < 2:
            return {
                "available": False,
                "reason": "insufficient_metrics",
                "metrics_used": logical_names,
                "sample_size": len(rows),
                "matrix": {},
                "pairwise": {},
                "highlights": {"strong_positive": [], "strong_negative": []},
                "strong_threshold": _STRONG_THRESHOLD,
            }

        n = len(rows)
        cols: list[np.ndarray] = []
        for rkey in row_keys:
            arr = np.full(n, np.nan, dtype=float)
            for i, row in enumerate(rows):
                if rkey not in row:
                    continue
                v = _as_float(row.get(rkey))
                if v is not None:
                    arr[i] = v
            cols.append(arr)

        matrix: dict[str, dict[str, float | None]] = {
            logical_names[i]: {logical_names[j]: None for j in range(len(logical_names))}
            for i in range(len(logical_names))
        }
        pairwise: dict[str, float] = {}

        for i in range(len(logical_names)):
            for j in range(i + 1, len(logical_names)):
                r_ij = _pearson_pair(cols[i], cols[j])
                a, b = logical_names[i], logical_names[j]
                matrix[a][b] = r_ij
                matrix[b][a] = r_ij
                if r_ij is not None:
                    key = f"{a}_vs_{b}"
                    pairwise[key] = round(r_ij, 4)
            matrix[logical_names[i]][logical_names[i]] = 1.0

        strong_pos: list[tuple[str, str, float]] = []
        strong_neg: list[tuple[str, str, float]] = []
        for i in range(len(logical_names)):
            for j in range(i + 1, len(logical_names)):
                r_ij = matrix[logical_names[i]][logical_names[j]]
                if r_ij is None:
                    continue
                pair = (logical_names[i], logical_names[j], r_ij)
                if r_ij >= _STRONG_THRESHOLD:
                    strong_pos.append(pair)
                elif r_ij <= -_STRONG_THRESHOLD:
                    strong_neg.append(pair)

        strong_pos.sort(key=lambda t: t[2], reverse=True)
        strong_neg.sort(key=lambda t: t[2])

        return {
            "available": True,
            "reason": None,
            "metrics_used": logical_names,
            "sample_size": n,
            "matrix": matrix,
            "pairwise": pairwise,
            "highlights": {
                "strong_positive": [
                    {"metric_a": a, "metric_b": b, "r": round(r, 4)} for a, b, r in strong_pos
                ],
                "strong_negative": [
                    {"metric_a": a, "metric_b": b, "r": round(r, 4)} for a, b, r in strong_neg
                ],
            },
            "strong_threshold": _STRONG_THRESHOLD,
        }
