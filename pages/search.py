import streamlit as st

from src.core.app_state import get_app
from src.core.session import get_user_id
from src.ui.project_selector import render_project_selector
from src.ui.layout import apply_layout

apply_layout()

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-badge">Search</div>
        <h1 class="hero-title">Inspect vector retrieval</h1>
        <p class="hero-subtitle">
            Debug retrieval quality by querying the active vector store directly.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

app = get_app()
user_id = get_user_id()

project_id = render_project_selector("Project for search")

if not project_id:
    st.stop()

project = app.get_project(user_id, project_id)

query = st.text_input("Search query", placeholder="Type a semantic query...")

if query:
    docs = app.vectorstore_service.similarity_search(project, query, k=3)

    if not docs:
        st.info("No documents found.")
        st.stop()

    st.metric("Retrieved chunks", len(docs))

    st.markdown("### Retrieved Documents")

    for doc in docs:
        file_name = doc.metadata.get("file_name", "unknown")
        chunk_id = doc.metadata.get("chunk_id", "?")

        st.markdown(
            f"""
            <div class="source-card">
                <div class="source-title">{file_name} — chunk {chunk_id}</div>
                <div class="source-preview">{doc.page_content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
