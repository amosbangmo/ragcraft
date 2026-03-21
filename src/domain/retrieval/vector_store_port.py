from __future__ import annotations

from typing import Protocol, runtime_checkable

from langchain_core.documents import Document

from src.domain.project import Project


@runtime_checkable
class VectorStorePort(Protocol):
    """Project-scoped dense retrieval index: load, mutate, and similarity search."""

    def load(self, project: Project) -> object | None: ...

    def index_documents(self, project: Project, chunks: list[Document]) -> tuple[object | None, float]: ...

    def delete_documents(self, project: Project, doc_ids: list[str]) -> object | None: ...

    def similarity_search(self, project: Project, query: str, k: int = 3) -> list[Document]: ...
