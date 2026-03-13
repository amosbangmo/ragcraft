import streamlit as st

from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.auth.guards import require_authentication


require_authentication("pages/evaluation.py")
apply_layout()


def render_eval_raw_assets(raw_assets):
    if not raw_assets:
        return

    for i, asset in enumerate(raw_assets, start=1):
        source_file = asset.get("source_file", "unknown")
        content_type = asset.get("content_type", "unknown")
        raw_content = asset.get("raw_content", "")

        with st.expander(f"Raw source {i} — {source_file} / {content_type}"):
            if content_type == "image":
                st.caption("Image stored as base64 in SQLite.")
                st.code(raw_content[:1000] + ("..." if len(raw_content) > 1000 else ""))
            else:
                st.write(raw_content)


header = render_page_header(
    badge="Evaluation",
    title="Test answer quality",
    subtitle="Run evaluation queries and inspect confidence and retrieved evidence.",
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
    st.markdown('<div class="card-subtitle">Review the raw text, tables, or images used to support the answer.</div>', unsafe_allow_html=True)
    render_eval_raw_assets(response.raw_assets)
    st.markdown("</div>", unsafe_allow_html=True)
