"""
Reports tab: benchmark export downloads and run metadata summary.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

def _is_benchmark_export_artifact(obj: Any) -> bool:
    """
    Structural check so export UI survives Streamlit hot-reload (multiple class objects
    for the same dataclass name).
    """
    if obj is None:
        return False
    required = (
        "metadata",
        "json_bytes",
        "csv_bytes",
        "markdown_bytes",
        "json_filename",
        "csv_filename",
        "markdown_filename",
    )
    return all(hasattr(obj, name) for name in required)


def render_evaluation_reports_tab(reports_payload: dict[str, Any]) -> None:
    st.markdown("### Reports & exports")
    st.caption(
        "Structured benchmark reports (JSON, CSV, Markdown) from the latest **dataset evaluation** run in this session."
    )

    export = reports_payload.get("export")
    if not _is_benchmark_export_artifact(export):
        st.info(
            "No benchmark export yet. Run **dataset evaluation** above when your gold QA dataset has entries; "
            "download links will appear in this section."
        )
        return

    run_id = getattr(export, "run_id", None)
    meta = export.metadata

    st.markdown("#### Export summary")
    bullets = [
        f"- **Project:** `{meta.project_id}`",
        f"- **Generated (UTC):** {meta.generated_at_utc}",
        f"- **Query rewrite:** {'on' if meta.enable_query_rewrite else 'off'}",
        f"- **Hybrid retrieval:** {'on' if meta.enable_hybrid_retrieval else 'off'}",
    ]
    if run_id:
        bullets.append(
            f"- **Run ID:** `{run_id}` — embedded in the JSON export and Markdown run context."
        )
    else:
        bullets.append(
            "- **Run ID:** not present on this payload (exports still include all row and summary data)."
        )
    bullets.extend(
        [
            "- **JSON:** richest artifact (summary, rows, optional correlations, failures, auto_debug, run_id).",
            "- **CSV:** one row per question; nested lists/dicts are JSON strings in cells.",
            "- **Markdown:** tables plus a **Notes** section (judge vs pipeline semantics) and optional auto-debug / failure blocks.",
        ]
    )
    st.markdown("\n".join(bullets))

    with st.expander("Raw export metadata (JSON)", expanded=False):
        st.json(meta.to_dict())

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
