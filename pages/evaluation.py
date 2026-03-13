import base64
import json

import streamlit as st

from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.auth.guards import require_authentication


require_authentication("pages/evaluation.py")
apply_layout()


def _render_image_asset(base64_content: str, title: str | None = None):
    try:
        image_bytes = base64.b64decode(base64_content)
        if title:
            st.markdown(f"**{title}**")
        st.image(image_bytes)
    except Exception:
        st.warning("Unable to render image asset.")


def _parse_table_raw_content(raw_content: str) -> dict:
    try:
        payload = json.loads(raw_content)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass

    return {
        "title": None,
        "html": None,
        "text": raw_content,
    }


def render_eval_raw_assets(raw_assets):
    if not raw_assets:
        return

    for i, asset in enumerate(raw_assets, start=1):
        source_file = asset.get("source_file", "unknown")
        content_type = asset.get("content_type", "unknown")
        raw_content = asset.get("raw_content", "")
        metadata = asset.get("metadata", {}) or {}

        table_title = metadata.get("table_title")
        image_title = metadata.get("image_title")
        page_number = metadata.get("page_number")

        title_parts = [f"Source {i} — {source_file}"]

        if content_type == "table" and table_title:
            title_parts.append(f"— {table_title}")
        elif content_type == "image" and image_title:
            title_parts.append(f"— {image_title}")
        elif page_number:
            title_parts.append(f"— page {page_number}")

        with st.expander(" ".join(title_parts)):
            if content_type == "text":
                st.write(raw_content)
                continue

            if content_type == "table":
                table_payload = _parse_table_raw_content(raw_content)
                parsed_table_title = table_payload.get("title")
                table_html = table_payload.get("html")
                table_text = table_payload.get("text")

                if parsed_table_title:
                    st.markdown(f"**{parsed_table_title}**")

                if table_html:
                    st.markdown(table_html, unsafe_allow_html=True)
                elif table_text:
                    st.write(table_text)
                else:
                    st.caption("Empty table payload.")
                continue

            if content_type == "image":
                _render_image_asset(raw_content, title=image_title)
                continue

            st.write(raw_content)


header = render_page_header(
    badge="Evaluation",
    title="Test answer quality",
    subtitle="Run evaluation queries and inspect the raw evidence used to generate the answer.",
    selector_label="Project for evaluation",
)

app = header["app"]
user_id = header["user_id"]
project_id = header["project_id"]

if not project_id:
    st.stop()

question = st.text_input("Evaluation question", placeholder="Enter a test question...")

if st.button("Run evaluation", use_container_width=True) and question:
    response = app.ask_question(
        user_id=user_id,
        project_id=project_id,
        question=question,
        chat_history=[],
    )

    if response is None:
        st.warning("No RAG response available.")
        st.stop()

    c1, c2 = st.columns([3, 1])

    with c1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Answer</div>', unsafe_allow_html=True)
        st.write(response.answer)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.metric("Confidence", response.confidence)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Raw evidence used</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">Review the raw text, tables, and extracted images selected after summary retrieval.</div>',
        unsafe_allow_html=True,
    )
    render_eval_raw_assets(response.raw_assets)
    st.markdown("</div>", unsafe_allow_html=True)
