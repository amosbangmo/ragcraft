"""
Evaluation — retrieval analytics tab: query log filters and dashboard.
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any, cast

import streamlit as st

from services.protocol import BackendClient
from components.shared.retrieval_dashboard import render_retrieval_dashboard


def render_evaluation_retrieval_tab(payload: dict[str, Any]) -> None:
    user_id = str(payload["user_id"])
    backend_client = cast(BackendClient, payload["backend_client"])
    project_id = str(payload["project_id"])
    wk = str(payload["widget_key_suffix"])

    st.caption(
        "Retrieval-focused KPIs and distributions from stored query logs (latency, confidence, hybrid usage). "
        "Use filters to narrow the window; logs are read from the application SQLite database."
    )

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Retrieval analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">Monitor latency and confidence for this project over recent queries.</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Filters", expanded=True):
        limit = int(
            st.number_input(
                "Max queries (most recent first)",
                min_value=10,
                max_value=20_000,
                value=500,
                step=50,
                key=f"ret_dash_limit_{wk}",
            )
        )
        use_range = st.checkbox(
            "Filter by UTC date range",
            value=False,
            key=f"ret_dash_use_range_{wk}",
        )
        since_utc = None
        until_utc = None
        if use_range:
            c1, c2 = st.columns(2)
            with c1:
                since_d = st.date_input("From (UTC)", key=f"ret_dash_since_{wk}")
            with c2:
                until_d = st.date_input("To (UTC)", key=f"ret_dash_until_{wk}")
            since_utc = datetime.combine(since_d, time.min, tzinfo=timezone.utc)
            until_utc = datetime.combine(until_d, time(23, 59, 59, 999999), tzinfo=timezone.utc)
            if since_utc > until_utc:
                st.warning("Start date is after end date; swap or adjust the range.")
                st.markdown("</div>", unsafe_allow_html=True)
                return

    since_iso = since_utc.isoformat() if since_utc is not None else None
    until_iso = until_utc.isoformat() if until_utc is not None else None
    logs = backend_client.list_retrieval_query_logs(
        user_id=user_id,
        project_id=project_id,
        since_iso=since_iso,
        until_iso=until_iso,
        last_n=limit,
    )

    render_retrieval_dashboard(logs)
    st.markdown("</div>", unsafe_allow_html=True)
