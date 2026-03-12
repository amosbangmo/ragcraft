import streamlit as st

from src.core.app_state import get_app
from src.core.session import get_user_id
from src.ui.project_selector import render_project_selector
from src.ui.layout import apply_layout

apply_layout()

def render_eval_sources(docs):
    if not docs:
        return

    for i, doc in enumerate(docs):
        file_name = doc.metadata.get("file_name", "unknown")
        chunk_id = doc.metadata.get("chunk_id", "?")
        preview = doc.page_content[:240]

        with st.expander(f"Source {i+1} — {file_name} / chunk {chunk_id}"):
            st.write(preview)


st.markdown(
    """
    <div class="hero-card">
        <div class="hero-badge">Evaluation</div>
        <h1 class="hero-title">Test answer quality</h1>
        <p class="hero-subtitle">
            Run evaluation queries and inspect confidence and retrieved evidence.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

app = get_app()
user_id = get_user_id()

project_id = render_project_selector("Project for evaluation")

if not project_id:
    st.stop()

question = st.text_input("Evaluation question", placeholder="Enter a test question...")

if st.button("Run evaluation", use_container_width=True) and question:
    response = app.ask_question(
        user_id=user_id,
        project_id=project_id,
        question=question,
        chat_history=[]
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
