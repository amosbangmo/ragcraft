import streamlit as st

from src.core.app_state import get_app
from src.core.session import get_user_id
from src.ui.project_selector import render_project_selector
from src.ui.layout import apply_layout

apply_layout()

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-badge">Ingestion</div>
        <h1 class="hero-title">Add documents to a project</h1>
        <p class="hero-subtitle">
            Upload PDF, DOCX or PPTX files and turn them into searchable chunks.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

app = get_app()
user_id = get_user_id()

st.markdown('<div class="section-card">', unsafe_allow_html=True)
project_id = render_project_selector("Project for ingestion")
st.markdown("</div>", unsafe_allow_html=True)

if not project_id:
    st.stop()

documents = app.list_project_documents(user_id, project_id)

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown(
        f"""
        <div class="section-card">
            <div class="card-title">Upload files</div>
            <div class="card-subtitle">Selected project: <b>{project_id}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.metric("Existing documents", len(documents))

uploaded_files = st.file_uploader(
    "Upload documents",
    type=["pdf", "docx", "pptx"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            chunks = app.ingest_uploaded_file(user_id, project_id, uploaded_file)
            st.success(f"{uploaded_file.name}: {len(chunks)} chunks created")

updated_documents = app.list_project_documents(user_id, project_id)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Documents in current project</div>', unsafe_allow_html=True)
st.markdown('<div class="card-subtitle">These files are currently available in the active workspace.</div>', unsafe_allow_html=True)

if updated_documents:
    for doc_name in updated_documents:
        st.markdown(f"- {doc_name}")
else:
    st.caption("No document ingested yet.")
st.markdown("</div>", unsafe_allow_html=True)
