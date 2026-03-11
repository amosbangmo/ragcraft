import os
from typing import List
from src.core.config import EMBEDDINGS
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

def create_vector_store(chunks: List[Document], project_path: str) -> FAISS:
    """
    Create a FAISS vector store while avoiding duplicate document indexing.

    Args:
        chunks: List of Document objects with metadata.
        project_path: Path to the current project folder.
    
    Returns:
        A FAISS vector store containing the new and existing chunks.
    """
    
    vector_store = load_vector_store(project_path)
    
    if vector_store is not None:
        existing_doc_ids = {doc.metadata["document_id"] for doc in vector_store.docstore._dict.values()}
    else:
        existing_doc_ids = set()

    new_chunks = [
        chunk for chunk in chunks if chunk.metadata["document_id"] not in existing_doc_ids
    ]

    if not new_chunks:
        print("All chunks are already indexed in FAISS!")
        return vector_store
    
    if vector_store is None:
        # No existing index → create a new one
        vector_store = FAISS.from_documents(new_chunks, EMBEDDINGS)
    else:
        # Add only new chunks to the existing index
        vector_store.add_documents(new_chunks)

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
        EMBEDDINGS,
        allow_dangerous_deserialization=True
    )

    return vector_store