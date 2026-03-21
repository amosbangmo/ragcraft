import time

from langchain_core.documents import Document

from src.domain.project import Project
from src.infrastructure.vectorstores.faiss.vector_store import (
    load_vector_store,
    save_vector_store,
    create_or_update_vector_store,
    delete_documents_from_vector_store,
)
from src.core.exceptions import VectorStoreError


# TODO(clean-arch): implement VectorStorePort; keep FAISS details behind this façade.

class VectorStoreService:
    """
    Service responsible for loading, indexing and querying
    project-specific vector stores.
    """

    def load(self, project: Project):
        try:
            return load_vector_store(project.faiss_index_path)
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to load vector store for project '{project.project_id}': {exc}",
                user_message="Unable to load the vector index for the selected project.",
            ) from exc

    def index_documents(self, project: Project, chunks: list[Document]) -> tuple[object | None, float]:
        if not chunks:
            return None, 0.0

        t0 = time.perf_counter()
        try:
            vector_store = create_or_update_vector_store(
                chunks=chunks,
                index_path=project.faiss_index_path,
            )

            if vector_store is not None:
                save_vector_store(vector_store, project.faiss_index_path)

            indexing_ms = (time.perf_counter() - t0) * 1000.0
            return vector_store, indexing_ms
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to index documents for project '{project.project_id}': {exc}",
                user_message="Unable to update the FAISS index for this project.",
            ) from exc

    def delete_documents(self, project: Project, doc_ids: list[str]):
        if not doc_ids:
            return None

        try:
            vector_store = delete_documents_from_vector_store(
                index_path=project.faiss_index_path,
                doc_ids=doc_ids,
            )

            if vector_store is not None:
                save_vector_store(vector_store, project.faiss_index_path)

            return vector_store
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to delete vectors for project '{project.project_id}': {exc}",
                user_message="Unable to update the FAISS index while deleting document vectors.",
            ) from exc

    def similarity_search(self, project: Project, query: str, k: int = 3):
        try:
            vector_store = self.load(project)

            if vector_store is None:
                return []

            return vector_store.similarity_search(query, k=k)
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to perform similarity search for project '{project.project_id}': {exc}",
                user_message="Unable to query the FAISS index for this project.",
            ) from exc
