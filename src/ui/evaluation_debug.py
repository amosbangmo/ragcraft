"""
Advanced debugging: full benchmark dashboard, JSON payloads, and raw manual assets.
"""

from __future__ import annotations

import streamlit as st

from src.domain.benchmark_result import BenchmarkResult
from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.ui.evaluation_dashboard import render_evaluation_dashboard
from src.ui.raw_assets import render_raw_assets


def render_evaluation_debug(
    *,
    benchmark_result: BenchmarkResult | None = None,
    manual_result: ManualEvaluationResult | None = None,
) -> None:
    """
    Technical inspection: full tables/charts for benchmarks and raw manual evaluation data.
    """
    st.caption("Advanced mode — technical inspection (full metrics, analytics, and raw payloads).")
    st.markdown("### Debug")

    if benchmark_result is None and manual_result is None:
        st.info("Run a manual evaluation or dataset evaluation to populate debug views.")
        return

    if benchmark_result is not None:
        summary = benchmark_result.summary.to_dict()
        rows = [row.to_dict() for row in benchmark_result.rows]
        st.markdown("#### Benchmark (full dashboard)")
        render_evaluation_dashboard(summary=summary, rows=rows)
        with st.expander("Benchmark summary JSON", expanded=False):
            st.json(summary)

    if manual_result is not None:
        st.markdown("#### Manual evaluation (technical)")
        with st.expander("Manual evaluation JSON", expanded=False):
            st.json(manual_result.to_dict())
        with st.expander("Raw evidence (full)", expanded=False):
            render_raw_assets(manual_result.raw_assets, mode="evaluation")
