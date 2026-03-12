from langchain_core.documents import Document
from src.domain.project import Project
from src.infrastructure.vectorstore.faiss_store import (
    create_vector_store,
    save_vector_store,
    load_vector_store,
)


class VectorStoreService:
    def load(self, project: Project):
        return load_vector_store(str(project.path))

    def index_documents(self, project: Project, chunks: list[Document]):
        vector_store = create_vector_store(chunks, str(project.path))
        save_vector_store(vector_store, str(project.path))
        return vector_store

    def similarity_search(self, project: Project, query: str, k: int = 3):
        vector_store = self.load(project)
        if vector_store is None:
            return []
        return vector_store.similarity_search(query, k=k)
