"""Compatibility re-exports. Prefer :mod:`src.infrastructure.vectorstores.faiss.vector_store`."""

from src.infrastructure.vectorstores.faiss.vector_store import (
    FAISSVectorStoreAdapter,
    create_or_update_vector_store,
    delete_documents_from_vector_store,
    load_vector_store,
    save_vector_store,
)

__all__ = [
    "FAISSVectorStoreAdapter",
    "create_or_update_vector_store",
    "delete_documents_from_vector_store",
    "load_vector_store",
    "save_vector_store",
]
