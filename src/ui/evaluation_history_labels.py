"""Pure helpers for benchmark run history labels (dataset evaluation tab)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.frontend_gateway.view_models import format_bool_toggle_on_off


def build_benchmark_history_entry_label(
    *,
    generated_at: object,
    run_id: str | None,
    enable_query_rewrite: bool | None,
    enable_hybrid_retrieval: bool | None,
    fallback_run_number: int,
) -> str:
    """
    Human-readable label stored with each history snapshot (timestamp, run id snippet, settings).
    ``fallback_run_number`` is used when no timestamp, id, or settings bits apply (1-based).
    """
    rid = (run_id or "")[:12]
    if isinstance(generated_at, datetime):
        tlabel = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    else:
        tlabel = str(generated_at)[:32] if generated_at else ""
    qr_on = enable_query_rewrite is True
    hy_on = enable_hybrid_retrieval is True
    settings_bits: list[str] = []
    if enable_query_rewrite is not None:
        settings_bits.append(f"query rewrite {format_bool_toggle_on_off(qr_on)}")
    if enable_hybrid_retrieval is not None:
        settings_bits.append(f"hybrid {format_bool_toggle_on_off(hy_on)}")
    settings = " · ".join(settings_bits)
    if rid and settings:
        return f"{tlabel} · {rid} · {settings}"
    if rid:
        return f"{tlabel} · {rid}"
    if settings:
        return f"{tlabel} · {settings}" if tlabel else settings
    return tlabel or f"run {fallback_run_number}"


def format_benchmark_run_selector_label(entry: dict[str, Any], index: int) -> str:
    """Selectbox display string for A/B comparison (appends id snippet and QR/Hyb when known)."""
    lab = entry.get("label")
    rid = entry.get("run_id") or ""
    short = f"{rid[:8]}…" if len(rid) > 8 else rid
    base = lab if isinstance(lab, str) else f"Run {index + 1}"
    parts: list[str] = [f"{base} ({short})" if short else base]
    qr = entry.get("enable_query_rewrite")
    hy = entry.get("enable_hybrid_retrieval")
    if isinstance(qr, bool) and isinstance(hy, bool):
        parts.append(
            f"QR {format_bool_toggle_on_off(qr)} · Hyb {format_bool_toggle_on_off(hy)}"
        )
    return " — ".join(parts)
