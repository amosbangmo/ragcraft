"""Shared Streamlit helpers for benchmark summary metrics (dataset tab + dashboard)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from components.shared.metric_help import render_metric_with_help


def coerce_float_for_summary_metric(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def render_summary_metric_from_mapping(
    data: Mapping[str, Any],
    key: str,
    label: str,
    *,
    as_percent: bool = False,
) -> None:
    raw = data.get(key)
    num = coerce_float_for_summary_metric(raw)
    if num is None:
        render_metric_with_help(label=label, value="—", metric_key=key)
        return
    if as_percent:
        render_metric_with_help(label=label, value=f"{num * 100:.1f}%", metric_key=key)
    else:
        render_metric_with_help(label=label, value=num, metric_key=key)
