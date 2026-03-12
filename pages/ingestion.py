import streamlit as st
from src.app.ragcraft_app import RAGCraftApp

app = RAGCraftApp()

project_id = st.session_state.get("project_id")
user_id = st.session_state.get("user_id")

if not project_id:
    st.warning("Please select a project first")
    st.stop()

st.header(f"📄 Document Ingestion for {project_id}")

uploaded_files = st.file_uploader(
    "Upload documents",
    type=["pdf", "docx", "pptx"],
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            chunks = app.ingest_uploaded_file(user_id, project_id, uploaded_file)
            st.success(f"{uploaded_file.name}: {len(chunks)} chunks created")
