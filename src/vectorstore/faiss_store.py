import os
from src.core.config import EMBEDDINGS
from langchain_community.vectorstores import FAISS

def create_vector_store(chunks):

    vector_store = FAISS.from_documents(
        chunks,
        EMBEDDINGS
    )

    return vector_store


def save_vector_store(vector_store, project_path):

    index_path = os.path.join(project_path, "faiss_index")

    vector_store.save_local(index_path)


def load_vector_store(project_path):

    index_path = os.path.join(project_path, "faiss_index")

    if not os.path.exists(index_path):
        return None

    vector_store = FAISS.load_local(
        index_path,
        EMBEDDING_MODEL,
        allow_dangerous_deserialization=True
    )

    return vector_store