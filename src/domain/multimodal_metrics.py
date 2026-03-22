"""
Modality detection and aggregate metrics for benchmark / evaluation rows.

Uses ``content_type`` on prompt assets and prompt sources (``text`` | ``table`` | ``image``),
aligned with :class:`~src.domain.retrieved_asset.RetrievedAsset` and RAG pipeline payloads.

Aggregates such as ``table_usage_rate`` belong to the ``multimodal`` family in
:mod:`src.domain.benchmark_metric_taxonomy`.
"""

from __future__ import annotations

from typing import Any


def _norm_content_type(raw: object) -> str:
    s = str(raw or "").strip().lower()
    if s in ("text", "table", "image"):
        return s
    return ""


def analyze_prompt_asset_modalities(assets: list[Any]) -> dict[str, Any]:
    """Aligned with :class:`~src.application.chat.multimodal_prompt_hints.MultimodalPromptHints.analyze_modalities`."""
    has_text = False
    has_table = False
    has_image = False
    for asset in assets or []:
        if not isinstance(asset, dict):
            continue
        ct = _norm_content_type(asset.get("content_type"))
        if ct == "text":
            has_text = True
        elif ct == "table":
            has_table = True
        elif ct == "image":
            has_image = True
    modality_count = sum((has_text, has_table, has_image))
    return {
        "has_text": has_text,
        "has_table": has_table,
        "has_image": has_image,
        "modality_count": modality_count,
        "mixed_modality_prompt": modality_count >= 2,
    }


def analyze_prompt_source_modalities(prompt_sources: list[Any]) -> dict[str, Any]:
    has_table = False
    has_image = False
    has_text = False
    for ref in prompt_sources or []:
        if not isinstance(ref, dict):
            continue
        ct = _norm_content_type(ref.get("content_type"))
        if ct == "text":
            has_text = True
        elif ct == "table":
            has_table = True
        elif ct == "image":
            has_image = True
    return {
        "has_text": has_text,
        "has_table": has_table,
        "has_image": has_image,
    }


def empty_modality_row_fields() -> dict[str, Any]:
    return {
        "modality_evaluation_available": False,
        "retrieval_has_table": False,
        "retrieval_has_image": False,
        "retrieval_has_text": False,
        "prompt_source_has_table": False,
        "prompt_source_has_image": False,
        "prompt_source_has_text": False,
        "context_uses_table": False,
        "context_uses_image": False,
        "mixed_modality_prompt": False,
        "prompt_modality_count": 0,
    }


def modality_row_fields_from_pipeline(pipeline: dict[str, Any]) -> dict[str, Any]:
    assets = pipeline.get("prompt_context_assets")
    if not isinstance(assets, list) or not assets:
        raw = pipeline.get("reranked_raw_assets")
        assets = raw if isinstance(raw, list) else []
    refs = pipeline.get("prompt_sources")
    if not isinstance(refs, list):
        refs = []

    pa = analyze_prompt_asset_modalities(assets)
    ca = analyze_prompt_source_modalities(refs)

    return {
        "modality_evaluation_available": True,
        "retrieval_has_table": bool(pa["has_table"]),
        "retrieval_has_image": bool(pa["has_image"]),
        "retrieval_has_text": bool(pa["has_text"]),
        "prompt_source_has_table": bool(ca["has_table"]),
        "prompt_source_has_image": bool(ca["has_image"]),
        "prompt_source_has_text": bool(ca["has_text"]),
        "context_uses_table": bool(pa["has_table"] or ca["has_table"]),
        "context_uses_image": bool(pa["has_image"] or ca["has_image"]),
        "mixed_modality_prompt": bool(pa["mixed_modality_prompt"]),
        "prompt_modality_count": int(pa["modality_count"] or 0),
    }


def _mean_float(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def aggregate_multimodal_metrics(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Aggregate usage and conditional quality metrics over rows that ran a successful pipeline.

    Returns ``None`` when no row reported ``modality_evaluation_available`` (e.g. all pipeline failures).
    """
    eligible = [r for r in rows if r.get("modality_evaluation_available") is True]
    if not eligible:
        return None

    n = len(eligible)
    table_n = sum(1 for r in eligible if r.get("context_uses_table"))
    image_n = sum(1 for r in eligible if r.get("context_uses_image"))
    multi_n = sum(1 for r in eligible if r.get("mixed_modality_prompt"))

    def _f(row: dict[str, Any], key: str) -> float | None:
        raw = row.get(key)
        if raw is None or isinstance(raw, bool):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def _groundedness(row: dict[str, Any]) -> float | None:
        return _f(row, "groundedness_score")

    table_f1: list[float] = []
    for r in eligible:
        if not r.get("context_uses_table"):
            continue
        if not r.get("has_expected_answer"):
            continue
        v = _f(r, "answer_f1")
        if v is not None:
            table_f1.append(v)

    image_ground: list[float] = []
    for r in eligible:
        if not r.get("context_uses_image"):
            continue
        v = _groundedness(r)
        if v is not None:
            image_ground.append(v)

    text_only_f1: list[float] = []
    with_table_f1: list[float] = []
    with_image_f1: list[float] = []
    text_only_g: list[float] = []
    with_table_g: list[float] = []
    with_image_g: list[float] = []

    for r in eligible:
        uses_t = bool(r.get("context_uses_table"))
        uses_i = bool(r.get("context_uses_image"))
        if r.get("has_expected_answer"):
            f1 = _f(r, "answer_f1")
            if f1 is not None:
                if not uses_t and not uses_i:
                    text_only_f1.append(f1)
                if uses_t:
                    with_table_f1.append(f1)
                if uses_i:
                    with_image_f1.append(f1)
        g = _groundedness(r)
        if g is not None:
            if not uses_t and not uses_i:
                text_only_g.append(g)
            if uses_t:
                with_table_g.append(g)
            if uses_i:
                with_image_g.append(g)

    has_multimodal_assets = table_n > 0 or image_n > 0

    by_modality: dict[str, Any] = {
        "text_only": {
            "row_count": sum(1 for r in eligible if not r.get("context_uses_table") and not r.get("context_uses_image")),
            "avg_answer_f1": _mean_float(text_only_f1),
            "avg_groundedness_score": _mean_float(text_only_g),
        },
        "with_table": {
            "row_count": table_n,
            "avg_answer_f1": _mean_float(with_table_f1),
            "avg_groundedness_score": _mean_float(with_table_g),
        },
        "with_image": {
            "row_count": image_n,
            "avg_answer_f1": _mean_float(with_image_f1),
            "avg_groundedness_score": _mean_float(with_image_g),
        },
    }

    return {
        "table_usage_rate": round(table_n / n, 2) if n else 0.0,
        "image_usage_rate": round(image_n / n, 2) if n else 0.0,
        "multimodal_answers_rate": round(multi_n / n, 2) if n else 0.0,
        "table_correctness": _mean_float(table_f1),
        "image_groundedness": _mean_float(image_ground),
        "eligible_rows": n,
        "has_multimodal_assets": has_multimodal_assets,
        "by_modality": by_modality,
    }
