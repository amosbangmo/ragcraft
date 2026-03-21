"""
Reports tab: benchmark export downloads and run metadata summary.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.services.benchmark_report_service import BenchmarkExportArtifacts


def render_evaluation_reports_tab(reports_payload: dict[str, Any]) -> None:
    st.markdown("### Reports & exports")
    st.caption(
        "Structured benchmark reports (JSON, CSV, Markdown) from the latest **dataset evaluation** run in this session."
    )

    export = reports_payload.get("export")
    if not isinstance(export, BenchmarkExportArtifacts):
        st.info(
            "No benchmark export yet. Run **dataset evaluation** above when your gold QA dataset has entries; "
            "download links will appear in this section."
        )
        return

    st.markdown("#### Run metadata")
    st.json(export.metadata.to_dict())

    dl1, dl2, dl3 = st.columns(3)
    with dl1:
        st.download_button(
            label="JSON report",
            data=export.json_bytes,
            file_name=export.json_filename,
            mime="application/json",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            label="CSV report",
            data=export.csv_bytes,
            file_name=export.csv_filename,
            mime="text/csv",
            use_container_width=True,
        )
    with dl3:
        st.download_button(
            label="Markdown report",
            data=export.markdown_bytes,
            file_name=export.markdown_filename,
            mime="text/markdown",
            use_container_width=True,
        )
