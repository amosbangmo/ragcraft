import streamlit as st

from src.app.ragcraft_app import RAGCraftApp
from src.core.session import get_user_id

st.title("🔎 Vector Search")

user_id = get_user_id()
project_id = st.session_state.get("project_id")

if not project_id:
    st.warning("Please select a project first.")
    st.stop()

app = RAGCraftApp()

project = app.get_project(user_id, project_id)

query = st.text_input("Search query")

if query:

    docs = app.vectorstore_service.similarity_search(project, query, k=3)

    if not docs:
        st.info("No documents found.")
        st.stop()

    st.markdown("### Retrieved Documents")

    for doc in docs:

        file_name = doc.metadata.get("file_name", "unknown")
        chunk_id = doc.metadata.get("chunk_id", "?")

        st.markdown(f"**{file_name} — chunk {chunk_id}**")
        st.write(doc.page_content)
        st.write("---")
