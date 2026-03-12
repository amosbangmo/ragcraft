import streamlit as st
from src.vectorstore.faiss_store import load_vector_store

st.title("Vector Search Test")

project = st.session_state.get("project_id")
user_id = st.session_state.get("user_id")

project_path = f"data/user_{user_id}/{project}"

vector_store = load_vector_store(project_path)

query = st.text_input("Search query")

if query and vector_store:

    docs = vector_store.similarity_search(query, k=3)

    for doc in docs:
        st.write(doc.page_content)
        st.write("---")
