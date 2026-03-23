"""
Retrieval analytics: aggregates and Streamlit visualizations over query logs.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import matplotlib.pyplot as plt
import streamlit as st

from services.api_client import parse_query_log_timestamp


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _latency_value(row: dict) -> float | None:
    return _as_float(row.get("latency_ms"))


def _confidence_value(row: dict) -> float | None:
    return _as_float(row.get("confidence"))


def distribution_buckets(
    values: Sequence[float], *, bin_count: int = 12
) -> tuple[list[float], list[int]]:
    """Fixed-width bins from min..max for lightweight testing and tables."""
    clean = sorted(v for v in values if v == v)  # drop NaN
    if not clean or bin_count < 1:
        return [], []
    lo, hi = clean[0], clean[-1]
    if lo == hi:
        return [lo], [len(clean)]
    width = (hi - lo) / bin_count
    edges = [lo + i * width for i in range(bin_count + 1)]
    counts = [0] * bin_count
    for v in clean:
        if v <= edges[0]:
            counts[0] += 1
            continue
        if v >= edges[-1]:
            counts[-1] += 1
            continue
        idx = int((v - lo) / width)
        idx = min(max(idx, 0), bin_count - 1)
        counts[idx] += 1
    return edges, counts


def compute_retrieval_dashboard_metrics(logs: Sequence[dict]) -> dict[str, Any]:
    latencies: list[float] = []
    confidences: list[float] = []
    hybrid_known: list[bool] = []
    lat_if_hybrid: list[float] = []
    lat_if_faiss: list[float] = []

    for row in logs:
        lat = _latency_value(row)
        if lat is not None:
            latencies.append(lat)
        conf = _confidence_value(row)
        if conf is not None:
            confidences.append(conf)
        if "hybrid_retrieval_enabled" in row:
            h = bool(row.get("hybrid_retrieval_enabled"))
            hybrid_known.append(h)
            if lat is not None:
                (lat_if_hybrid if h else lat_if_faiss).append(lat)

    n = len(logs)
    avg_lat = sum(latencies) / len(latencies) if latencies else None
    avg_conf = sum(confidences) / len(confidences) if confidences else None
    hybrid_rate = None
    if hybrid_known:
        hybrid_rate = sum(1 for x in hybrid_known if x) / len(hybrid_known)

    avg_lat_hybrid = sum(lat_if_hybrid) / len(lat_if_hybrid) if lat_if_hybrid else None
    avg_lat_faiss = sum(lat_if_faiss) / len(lat_if_faiss) if lat_if_faiss else None

    return {
        "total_queries": n,
        "avg_latency_ms": avg_lat,
        "avg_confidence": avg_conf,
        "hybrid_usage_rate": hybrid_rate,
        "hybrid_sample_count": len(hybrid_known),
        "latency_values": latencies,
        "confidence_values": confidences,
        "avg_latency_hybrid_ms": avg_lat_hybrid,
        "avg_latency_faiss_ms": avg_lat_faiss,
        "hybrid_latency_count": len(lat_if_hybrid),
        "faiss_latency_count": len(lat_if_faiss),
    }


def _truncate(text: str, max_len: int = 80) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _table_rows(logs: Sequence[dict], *, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in logs[:limit]:
        q = row.get("question")
        q_str = q if isinstance(q, str) else ("" if q is None else str(q))
        ts = parse_query_log_timestamp(row)
        ts_display = ts.isoformat() if ts else (row.get("timestamp") or "—")
        h = row.get("hybrid_retrieval_enabled")
        hybrid_display = "—"
        if h is not None:
            hybrid_display = "Yes" if h else "No"
        lat = row.get("latency_ms")
        conf = row.get("confidence")
        rows.append(
            {
                "Time (UTC)": ts_display,
                "Question": _truncate(q_str),
                "Latency ms": lat if lat is not None else "—",
                "Confidence": f"{conf:.3f}" if isinstance(conf, (int, float)) else "—",
                "Hybrid": hybrid_display,
            }
        )
    return rows


def _sort_logs_by_latency_desc(logs: Sequence[dict]) -> list[dict]:
    with_lat = [r for r in logs if _latency_value(r) is not None]
    return sorted(with_lat, key=lambda r: float(_latency_value(r) or 0.0), reverse=True)


def _sort_logs_by_confidence_asc(logs: Sequence[dict]) -> list[dict]:
    with_conf = [r for r in logs if _confidence_value(r) is not None]
    return sorted(with_conf, key=lambda r: float(_confidence_value(r) or 0.0))


def render_retrieval_dashboard(logs: list[dict]) -> None:
    if not logs:
        st.info(
            "No query logs match the current filters. Run queries from chat or evaluation to populate data."
        )
        return

    m = compute_retrieval_dashboard_metrics(logs)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if m["avg_latency_ms"] is not None:
            st.metric("Avg latency (ms)", f"{m['avg_latency_ms']:.1f}")
        else:
            st.metric("Avg latency (ms)", "—")
    with c2:
        if m["avg_confidence"] is not None:
            st.metric("Avg confidence", f"{m['avg_confidence']:.3f}")
        else:
            st.metric("Avg confidence", "—")
    with c3:
        st.metric("Total queries", str(m["total_queries"]))
    with c4:
        if m["hybrid_usage_rate"] is not None:
            st.metric("Hybrid usage", f"{100.0 * m['hybrid_usage_rate']:.1f}%")
        else:
            st.metric("Hybrid usage", "N/A")

    if (
        m["avg_latency_hybrid_ms"] is not None
        and m["avg_latency_faiss_ms"] is not None
        and m["hybrid_latency_count"] > 0
        and m["faiss_latency_count"] > 0
    ):
        with st.expander("Hybrid vs FAISS signals (from logged queries)", expanded=False):
            a1, a2, a3 = st.columns(3)
            with a1:
                st.metric("Avg latency hybrid (ms)", f"{m['avg_latency_hybrid_ms']:.1f}")
            with a2:
                st.metric("Avg latency FAISS-only (ms)", f"{m['avg_latency_faiss_ms']:.1f}")
            with a3:
                delta = m["avg_latency_hybrid_ms"] - m["avg_latency_faiss_ms"]
                st.metric("Δ latency (hybrid − FAISS)", f"{delta:+.1f} ms")

    hist_cols = st.columns(2)
    with hist_cols[0]:
        st.caption("Latency distribution (ms)")
        vals = m["latency_values"]
        if len(vals) >= 2:
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.hist(vals, bins=min(24, max(8, len(vals) // 3)))
            ax.set_xlabel("Latency (ms)")
            ax.set_ylabel("Count")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.caption("Not enough latency samples for a histogram.")

    with hist_cols[1]:
        st.caption("Confidence distribution")
        cvals = m["confidence_values"]
        if len(cvals) >= 2:
            fig2, ax2 = plt.subplots(figsize=(6, 3))
            ax2.hist(cvals, bins=min(20, max(8, len(cvals) // 3)))
            ax2.set_xlabel("Confidence")
            ax2.set_ylabel("Count")
            fig2.tight_layout()
            st.pyplot(fig2)
            plt.close(fig2)
        else:
            st.caption("Not enough confidence samples for a histogram.")

    st.subheader("Recent queries")
    st.dataframe(_table_rows(logs, limit=25), use_container_width=True, hide_index=True)

    st.subheader("Highest latency")
    st.dataframe(
        _table_rows(_sort_logs_by_latency_desc(logs), limit=15),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Lowest confidence")
    st.dataframe(
        _table_rows(_sort_logs_by_confidence_asc(logs), limit=15),
        use_container_width=True,
        hide_index=True,
    )
