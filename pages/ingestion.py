import streamlit as st

from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header


apply_layout()

header = render_page_header(
    badge="Ingestion",
    title="Add documents to a project",
    subtitle="Upload PDF, DOCX or PPTX files and turn them into searchable chunks.",
    selector_label="Project for ingestion",
)

app = header["app"]
user_id = header["user_id"]
project_id = header["project_id"]

if not project_id:
    st.stop()

documents = app.list_project_documents(user_id, project_id)

st.metric("Existing documents", len(documents))

uploaded_files = st.file_uploader(
    "Upload documents",
    type=["pdf", "docx", "pptx"],
    accept_multiple_files=True,
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
