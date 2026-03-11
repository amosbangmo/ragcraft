import streamlit as st
import os
from src.ingestion.loader import save_uploaded_file
from src.ingestion.parser import parse_document
from src.ingestion.chunker import create_chunks
from src.vectorstore.faiss_store import create_vector_store, save_vector_store

project = st.session_state.get("current_project")
user_id = st.session_state.get("user_id")

header_title = "📄 Document Ingestion"

if project:
    st.header(f"{header_title} for {project}")
else:
    st.header(header_title)
    st.warning("Please select a project first")
    st.stop()

project_path = f"data/user_{user_id}/{project}"
os.makedirs(project_path, exist_ok=True)

uploaded_files = st.file_uploader(
    "Upload documents",
    type=["pdf", "docx", "pptx"],
    accept_multiple_files=True
)

if uploaded_files:
    for file in uploaded_files:
        with st.spinner(f"Processing {file.name}..."):
            file_path = save_uploaded_file(file, project_path)
            text = parse_document(file_path)
            chunks = create_chunks(text, project, file.name)
            vector_store = create_vector_store(chunks, project)
            save_vector_store(
                vector_store,
                project_path
            )
            st.success(f"{file.name}: {len(chunks)} chunks created")
