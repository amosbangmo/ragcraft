import time

from langchain_core.documents import Document

from domain.common.ports.project_chain_handle_cache_port import ProjectChainHandleCachePort
from domain.projects.project import Project
from domain.rag.summary_recall_document import SummaryRecallDocument
from infrastructure.config.exceptions import VectorStoreError
from infrastructure.persistence.caching.process_project_chain_cache import (
    get_default_process_project_chain_cache,
)
from infrastructure.rag.summary_recall_document_adapter import (
    langchain_document_from_summary_recall,
    summary_recall_document_from_langchain,
)
from infrastructure.rag.vectorstores.faiss.vector_store import (
    create_or_update_vector_store,
    delete_documents_from_vector_store,
    load_vector_store,
    save_vector_store,
)


class VectorStoreService:
    """
    FAISS-backed implementation of :class:`~domain.rag.retrieval.vector_store_port.VectorStorePort`.

    ``load`` consults an in-process :class:`~domain.common.ports.project_chain_handle_cache_port.ProjectChainHandleCachePort`
    so repeated retrieval work reuses the same handle until :meth:`ProjectChainHandleCachePort.drop` runs
    (ingestion / explicit cache invalidation).
    """

    def __init__(
        self,
        *,
        chain_cache: ProjectChainHandleCachePort | None = None,
    ) -> None:
        self._chain_cache: ProjectChainHandleCachePort = (
            chain_cache if chain_cache is not None else get_default_process_project_chain_cache()
        )

    def load(self, project: Project):
        project_id = project.project_id
        cached = self._chain_cache.get(project_id)
        if cached is not None:
            return cached
        try:
            loaded = load_vector_store(project.faiss_index_path)
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to load vector store for project '{project_id}': {exc}",
                user_message="Unable to load the vector index for the selected project.",
            ) from exc
        self._chain_cache.set(project_id, loaded)
        return loaded

    def index_documents(
        self, project: Project, chunks: list[SummaryRecallDocument]
    ) -> tuple[object | None, float]:
        if not chunks:
            return None, 0.0

        lc_chunks: list[Document] = [langchain_document_from_summary_recall(c) for c in chunks]

        t0 = time.perf_counter()
        try:
            vector_store = create_or_update_vector_store(
                chunks=lc_chunks,
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

    def similarity_search(
        self, project: Project, query: str, k: int = 3
    ) -> list[SummaryRecallDocument]:
        try:
            vector_store = self.load(project)

            if vector_store is None:
                return []

            raw = vector_store.similarity_search(query, k=k)
            return [summary_recall_document_from_langchain(d) for d in raw]
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to perform similarity search for project '{project.project_id}': {exc}",
                user_message="Unable to query the FAISS index for this project.",
            ) from exc
