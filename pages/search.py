import streamlit as st

from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.auth.guards import require_authentication


require_authentication("pages/search.py")
apply_layout()


header = render_page_header(
    badge="Search",
    title="Inspect vector retrieval",
    subtitle="Debug retrieval quality by querying the active vector store directly.",
    selector_label="Project for search",
)

app = header["app"]
user_id = header["user_id"]
project_id = header["project_id"]

if not project_id:
    st.stop()

project = app.get_project(user_id, project_id)

query = st.text_input("Search query", placeholder="Type a semantic query...")

if query:
    docs = app.vectorstore_service.similarity_search(project, query, k=5)

    if not docs:
        st.info("No documents found.")
        st.stop()

    st.metric("Retrieved summaries", len(docs))
    st.markdown("### Retrieved summaries from FAISS")

    for doc in docs:
        file_name = doc.metadata.get("file_name", "unknown")
        doc_id = doc.metadata.get("doc_id", "?")
        content_type = doc.metadata.get("content_type", "unknown")

        st.markdown(
            f"""
            <div class="source-card">
                <div class="source-title">{file_name} — {content_type} — doc_id {doc_id}</div>
                <div class="source-preview">{doc.page_content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
