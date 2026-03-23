from datetime import datetime
from pathlib import Path

import streamlit as st

from components.shared.document_actions import is_document_reindexing


def inject_document_table_styles():
    st.markdown(
        """
        <style>
        .rc-doc-empty {
            padding: 16px;
            border-radius: 14px;
            background: #ffffff;
            border: 1px dashed rgba(15,23,42,0.12);
            color: #64748b;
            text-align: center;
        }

        .rc-doc-title {
            font-weight: 650;
            color: #0f172a;
            line-height: 1.3;
            margin-bottom: 2px;
        }

        .rc-doc-subtitle {
            color: #64748b;
            font-size: 0.86rem;
            margin-bottom: 8px;
        }

        [class*="st-key-doc-card"] {
            background: #ffffff !important;
            border-radius: 16px !important;
        }

        [class*="st-key-doc-card"] > div {
            background: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _get_file_badge_and_icon(filename: str) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return "PDF", "📄"
    if suffix == ".docx":
        return "DOCX", "📝"
    if suffix == ".pptx":
        return "PPTX", "📊"

    return suffix.replace(".", "").upper() or "FILE", "📁"


def _format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _format_ingested_at(created_at: str | None) -> str:
    if not created_at:
        return "Unknown"

    try:
        dt = datetime.fromisoformat(created_at)
        return dt.strftime("%d %b %Y, %H:%M")
    except Exception:
        return created_at


def render_document_table(
    *,
    documents: list[dict],
    key_prefix: str,
):
    inject_document_table_styles()

    if not documents:
        st.markdown(
            '<div class="rc-doc-empty">No document ingested yet.</div>',
            unsafe_allow_html=True,
        )
        return None

    selected_action = None

    for index, doc in enumerate(documents):
        doc_name = doc["name"]
        project_id = doc.get("project_id") or key_prefix.split("_", 1)[-1]
        size_bytes = int(doc.get("size_bytes", 0))
        asset_count = int(doc.get("asset_count", 0))
        text_count = int(doc.get("text_count", 0))
        table_count = int(doc.get("table_count", 0))
        image_count = int(doc.get("image_count", 0))
        latest_ingested_at = _format_ingested_at(doc.get("latest_ingested_at"))
        is_reindexing = is_document_reindexing(project_id, doc_name)

        badge, icon = _get_file_badge_and_icon(doc_name)
        size_label = _format_file_size(size_bytes)
        asset_label = f"{asset_count} asset" if asset_count == 1 else f"{asset_count} assets"
        composition_label = f"{text_count} text / {table_count} table / {image_count} image"

        with st.container(border=True, key=f"doc-card-{key_prefix}-{index}"):
            col_main, col_actions = st.columns([8, 4], vertical_alignment="center")

            with col_main:
                icon_col, body_col = st.columns([1, 12], vertical_alignment="top")

                with icon_col:
                    st.write("")
                    st.markdown(f"### {icon}")

                with body_col:
                    st.markdown(f'<div class="rc-doc-title">{doc_name}</div>', unsafe_allow_html=True)
                    st.markdown(
                        '<div class="rc-doc-subtitle">Indexed and available in the current workspace</div>',
                        unsafe_allow_html=True,
                    )

                    if is_reindexing:
                        st.warning(
                            f"⏳ Reindexing in progress — {badge} • {size_label} • {asset_label}"
                        )
                    else:
                        st.caption(f"{badge} • {size_label} • {asset_label}")

                    st.caption(f"Composition: {composition_label}")
                    st.caption(f"Ingested: {latest_ingested_at}")

            with col_actions:
                action_cols = st.columns([1.3, 1.3, 1.0])

                with action_cols[0]:
                    inspect_clicked = st.button(
                        "Inspect",
                        key=f"{key_prefix}_inspect_{index}_{doc_name}",
                        use_container_width=True,
                        disabled=is_reindexing,
                    )

                with action_cols[1]:
                    reindex_clicked = st.button(
                        "Reindex",
                        key=f"{key_prefix}_reindex_{index}_{doc_name}",
                        use_container_width=True,
                        disabled=is_reindexing,
                    )

                with action_cols[2]:
                    delete_clicked = st.button(
                        "Delete",
                        key=f"{key_prefix}_delete_{index}_{doc_name}",
                        use_container_width=True,
                        disabled=is_reindexing,
                    )

                if inspect_clicked:
                    selected_action = {"action": "inspect", "doc_name": doc_name}

                if reindex_clicked:
                    selected_action = {"action": "reindex", "doc_name": doc_name}

                if delete_clicked:
                    selected_action = {"action": "delete", "doc_name": doc_name}

    return selected_action
