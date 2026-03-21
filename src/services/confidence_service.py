"""
Pipeline confidence from reranked retrieval evidence only.

Separate from LLM-judge metrics (groundedness, hallucination, answer relevance).
"""

from __future__ import annotations

import math
from collections.abc import Iterable


class ConfidenceService:
    """Combines rerank strength, consistency, and support breadth into [0, 1]."""

    _W_TOP = 0.4
    _W_AVG = 0.3
    _W_GAP = 0.2
    _W_COUNT = 0.1
    _COUNT_CAP = 5

    def compute_confidence(
        self,
        *,
        reranked_raw_assets: list[dict],
    ) -> float:
        scores = _extract_rerank_scores(reranked_raw_assets)
        if not scores:
            return 0.0

        normalized = [_sigmoid(s) for s in scores]
        top_n = normalized[0]
        avg_n = sum(normalized) / len(normalized)

        if len(normalized) >= 2:
            gap_n = max(0.0, min(1.0, normalized[0] - normalized[1]))
        else:
            gap_n = 0.0

        count_factor = min(len(scores) / self._COUNT_CAP, 1.0)
        diversity_factor = _source_diversity_ratio(reranked_raw_assets)
        support_signal = 0.65 * count_factor + 0.35 * diversity_factor

        blended = (
            self._W_TOP * top_n
            + self._W_AVG * avg_n
            + self._W_GAP * gap_n
            + self._W_COUNT * support_signal
        )

        out = max(0.0, min(1.0, blended))
        return round(out, 2)


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _asset_metadata(asset: dict) -> dict:
    meta = asset.get("metadata")
    return meta if isinstance(meta, dict) else {}


def _source_diversity_ratio(assets: list[dict]) -> float:
    """Distinct ``source_file`` share among selected assets; neutral when unlabeled."""
    n = len(assets)
    if n == 0:
        return 0.0
    paths = [a.get("source_file") for a in assets]
    if not any(p is not None and str(p).strip() for p in paths):
        return 1.0
    distinct = len({str(p) for p in paths if p is not None and str(p).strip()})
    return min(1.0, distinct / n)


def _extract_rerank_scores(assets: Iterable[dict]) -> list[float]:
    ordered: list[float] = []
    for asset in assets:
        meta = _asset_metadata(asset)
        raw = meta.get("rerank_score")
        if raw is None:
            continue
        try:
            ordered.append(float(raw))
        except (TypeError, ValueError):
            continue
    return ordered
