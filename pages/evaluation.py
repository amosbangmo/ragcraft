import streamlit as st

from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.auth.guards import require_authentication


apply_layout()
require_authentication("pages/evaluation.py")


def render_eval_sources(docs):
    if not docs:
        return

    for i, doc in enumerate(docs):
        file_name = doc.metadata.get("file_name", "unknown")
        chunk_id = doc.metadata.get("chunk_id", "?")
        preview = doc.page_content[:240]

        with st.expander(f"Source {i+1} — {file_name} / chunk {chunk_id}"):
            st.write(preview)


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
    st.markdown('<div class="card-title">Retrieved evidence</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-subtitle">Review the chunks used to support the answer.</div>', unsafe_allow_html=True)
    render_eval_sources(response.source_documents)
    st.markdown("</div>", unsafe_allow_html=True)
