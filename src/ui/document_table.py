from datetime import datetime
from pathlib import Path

import streamlit as st


def inject_document_table_styles():
    st.markdown(
        """
        <style>
        .rc-doc-main {
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 0;
        }

        .rc-doc-icon {
            width: 38px;
            height: 38px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f8fafc;
            border: 1px solid rgba(15,23,42,0.06);
            font-size: 1rem;
            flex-shrink: 0;
        }

        .rc-doc-meta {
            min-width: 0;
            flex: 1;
            padding-bottom: 8px;
        }

        .rc-doc-name {
            font-weight: 650;
            color: #0f172a;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            line-height: 1.3;
        }

        .rc-doc-subtitle {
            color: #64748b;
            font-size: 0.86rem;
            margin-top: 4px;
        }

        .rc-doc-badges {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
            margin-bottom: 6px;
        }

        .rc-doc-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(37,99,235,0.08);
            border: 1px solid rgba(37,99,235,0.16);
            color: #1d4ed8;
            font-size: 0.76rem;
            font-weight: 700;
        }

        .rc-doc-badge-neutral {
            background: rgba(15,23,42,0.05);
            border: 1px solid rgba(15,23,42,0.08);
            color: #475569;
        }

        .rc-doc-extra {
            color: #64748b;
            font-size: 0.84rem;
            margin-top: 4px;
            line-height: 1.5;
        }

        .rc-doc-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            flex-wrap: wrap;
        }

        .rc-doc-empty {
            padding: 16px;
            border-radius: 14px;
            background: #ffffff;
            border: 1px dashed rgba(15,23,42,0.12);
            color: #64748b;
            text-align: center;
        }

        div[data-testid="stButton"] button.rc-delete-icon-btn,
        .stButton > button.rc-delete-icon-btn {
            background: transparent !important;
            color: #dc2626 !important;
            border: none !important;
            box-shadow: none !important;
            width: 30px !important;
            height: 30px !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 0.95rem !important;
            line-height: 1 !important;
        }

        div[data-testid="stButton"] button.rc-delete-icon-btn:hover,
        .stButton > button.rc-delete-icon-btn:hover {
            background: rgba(220,38,38,0.08) !important;
            border-radius: 8px !important;
            color: #b91c1c !important;
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
        size_bytes = int(doc.get("size_bytes", 0))
        asset_count = int(doc.get("asset_count", 0))
        text_count = int(doc.get("text_count", 0))
        table_count = int(doc.get("table_count", 0))
        image_count = int(doc.get("image_count", 0))
        latest_ingested_at = _format_ingested_at(doc.get("latest_ingested_at"))

        badge, icon = _get_file_badge_and_icon(doc_name)
        size_label = _format_file_size(size_bytes)
        asset_label = f"{asset_count} asset" if asset_count == 1 else f"{asset_count} assets"
        composition_label = f"{text_count} text / {table_count} table / {image_count} image"

        with st.container(border=True, key=f"doc-card-{key_prefix}-{index}"):
            col_main, col_actions = st.columns([8, 4], vertical_alignment="center")

            with col_main:
                st.markdown(
                    f"""
                    <div class="rc-doc-main">
                        <div class="rc-doc-icon">{icon}</div>
                        <div class="rc-doc-meta">
                            <div class="rc-doc-name">{doc_name}</div>
                            <div class="rc-doc-subtitle">
                                Indexed and available in the current workspace
                            </div>
                            <div class="rc-doc-badges">
                                <span class="rc-doc-badge">{badge}</span>
                                <span class="rc-doc-badge rc-doc-badge-neutral">{size_label}</span>
                                <span class="rc-doc-badge rc-doc-badge-neutral">{asset_label}</span>
                            </div>
                            <div class="rc-doc-extra">
                                Composition: {composition_label}<br/>
                                Ingested: {latest_ingested_at}
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_actions:
                action_cols = st.columns([1.3, 1.3, 0.8])

                with action_cols[0]:
                    inspect_clicked = st.button(
                        "Inspect",
                        key=f"{key_prefix}_inspect_{index}_{doc_name}",
                        use_container_width=True,
                    )

                with action_cols[1]:
                    reindex_clicked = st.button(
                        "Reindex",
                        key=f"{key_prefix}_reindex_{index}_{doc_name}",
                        use_container_width=True,
                    )

                with action_cols[2]:
                    delete_clicked = st.button(
                        "🗑",
                        key=f"{key_prefix}_delete_{index}_{doc_name}",
                        help=f"Delete {doc_name}",
                    )

                st.markdown(
                    """
                    <script>
                    const buttons = window.parent.document.querySelectorAll('button');
                    buttons.forEach(btn => {
                        if (btn.innerText.trim() === '🗑') {
                            btn.classList.add('rc-delete-icon-btn');
                        }
                    });
                    </script>
                    """,
                    unsafe_allow_html=True,
                )

                if inspect_clicked:
                    selected_action = {"action": "inspect", "doc_name": doc_name}

                if reindex_clicked:
                    selected_action = {"action": "reindex", "doc_name": doc_name}

                if delete_clicked:
                    selected_action = {"action": "delete", "doc_name": doc_name}

    return selected_action
