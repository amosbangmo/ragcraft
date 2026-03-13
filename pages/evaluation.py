import base64

import streamlit as st

from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.ui.source_citations import render_source_citations
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
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")
        start_element_index = metadata.get("start_element_index")
        end_element_index = metadata.get("end_element_index")

        title_parts = [f"Source {i} — {source_file}"]

        if content_type == "table" and table_title:
            title_parts.append(f"— {table_title}")
        elif content_type == "image" and image_title:
            title_parts.append(f"— {image_title}")

        if page_number is not None:
            title_parts.append(f"— page {page_number}")
        elif page_start is not None and page_end is not None:
            if page_start == page_end:
                title_parts.append(f"— page {page_start}")
            else:
                title_parts.append(f"— pages {page_start}-{page_end}")

        if content_type == "text" and start_element_index is not None and end_element_index is not None:
            if start_element_index == end_element_index:
                title_parts.append(f"— element {start_element_index}")
            else:
                title_parts.append(f"— elements {start_element_index}-{end_element_index}")

        with st.expander(" ".join(title_parts)):
            if content_type == "text":
                st.write(raw_content)
                continue

            if content_type == "table":
                if table_title:
                    st.markdown(f"**{table_title}**")

                if raw_content:
                    st.markdown(raw_content, unsafe_allow_html=True)
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
    st.markdown('<div class="card-title">Source citations</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">Structured citation layer generated from the raw retrieved assets.</div>',
        unsafe_allow_html=True,
    )
    render_source_citations(response.citations)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Raw evidence used</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">Review the raw text, tables, and extracted images selected after summary retrieval.</div>',
        unsafe_allow_html=True,
    )
    render_eval_raw_assets(response.raw_assets)
    st.markdown("</div>", unsafe_allow_html=True)
