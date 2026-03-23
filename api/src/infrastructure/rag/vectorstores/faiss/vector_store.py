"""
FAISS + LangChain vector index lifecycle.

Used by :class:`~infrastructure.rag.vectorstore_service.VectorStoreService`.
"""

from __future__ import annotations

from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from infrastructure.config.config import EMBEDDINGS


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


def create_or_update_vector_store(chunks: list[Document], index_path: Path):
    """
    Create or update a FAISS vector store while avoiding duplicate
    indexing based on doc_id metadata.
    """
    if not chunks:
        return None

    ids = [chunk.metadata["doc_id"] for chunk in chunks]
    vector_store = load_vector_store(index_path)

    if vector_store is None:
        return FAISS.from_documents(
            documents=chunks,
            embedding=EMBEDDINGS,
            ids=ids,
        )

    existing_doc_ids = {doc.metadata.get("doc_id") for doc in vector_store.docstore._dict.values()}

    new_chunks = []
    new_ids = []

    for chunk, chunk_id in zip(chunks, ids):
        if chunk_id in existing_doc_ids:
            continue
        new_chunks.append(chunk)
        new_ids.append(chunk_id)

    if new_chunks:
        vector_store.add_documents(documents=new_chunks, ids=new_ids)

    return vector_store


def delete_documents_from_vector_store(index_path: Path, doc_ids: list[str]):
    """
    Delete documents from FAISS using doc_id as vector store id.
    """
    if not doc_ids:
        return None

    vector_store = load_vector_store(index_path)

    if vector_store is None:
        return None

    try:
        vector_store.delete(ids=doc_ids)
    except Exception:
        # If deletion fails for any reason, keep the store as-is.
        return vector_store

    return vector_store


class FAISSVectorStoreAdapter:
    """Explicit adapter around module-level FAISS helpers (same behavior as legacy imports)."""

    def load_vector_store(self, index_path: Path):
        return load_vector_store(index_path)

    def save_vector_store(self, vector_store, index_path: Path) -> None:
        save_vector_store(vector_store, index_path)

    def create_or_update_vector_store(self, chunks: list[Document], index_path: Path):
        return create_or_update_vector_store(chunks, index_path)

    def delete_documents_from_vector_store(self, index_path: Path, doc_ids: list[str]):
        return delete_documents_from_vector_store(index_path, doc_ids)
