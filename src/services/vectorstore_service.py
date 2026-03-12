from langchain_core.documents import Document

from src.domain.project import Project
from src.infrastructure.vectorstore.faiss_store import (
    load_vector_store,
    save_vector_store,
    create_or_update_vector_store,
)


class VectorStoreService:
    """
    Service responsible for loading, indexing and querying
    project-specific vector stores.
    """

    def load(self, project: Project):
        return load_vector_store(project.faiss_index_path)

    def index_documents(self, project: Project, chunks: list[Document]):
        vector_store = create_or_update_vector_store(
            chunks=chunks,
            index_path=project.faiss_index_path,
        )
        save_vector_store(vector_store, project.faiss_index_path)
        return vector_store

    def similarity_search(self, project: Project, query: str, k: int = 3):
        vector_store = self.load(project)

        if vector_store is None:
            return []

        return vector_store.similarity_search(query, k=k)
