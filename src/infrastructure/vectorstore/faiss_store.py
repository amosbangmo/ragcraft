from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from src.core.config import EMBEDDINGS


def load_vector_store(index_path: Path):
    """
    Load a FAISS vector store from disk.
    """
    if not index_path.exists():
        return None

    return FAISS.load_local(
        str(index_path),
        EMBEDDINGS,
        allow_dangerous_deserialization=True,
    )


def save_vector_store(vector_store, index_path: Path):
    """
    Save a FAISS vector store to disk.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(index_path))


def create_or_update_vector_store(chunks: List[Document], index_path: Path):
    """
    Create or update a FAISS vector store while avoiding duplicate
    indexing based on doc_id metadata.
    """
    if not chunks:
        return None

    vector_store = load_vector_store(index_path)

    if vector_store is None:
        return FAISS.from_documents(chunks, EMBEDDINGS)

    existing_doc_ids = {
        doc.metadata.get("doc_id")
        for doc in vector_store.docstore._dict.values()
    }

    new_chunks = [
        chunk for chunk in chunks
        if chunk.metadata.get("doc_id") not in existing_doc_ids
    ]

    if new_chunks:
        vector_store.add_documents(new_chunks)

    return vector_store
