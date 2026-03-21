"""
FastAPI dependency providers.

Composition root: a single :class:`~src.app.ragcraft_app.RAGCraftApp` instance (same graph as Streamlit).
Use-case and service getters are explicit factories for route handlers — no hidden globals beyond the
cached app.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.app.ragcraft_app import RAGCraftApp
from src.application.evaluation.use_cases.build_benchmark_export_artifacts import (
    BuildBenchmarkExportArtifactsUseCase,
)
from src.application.evaluation.use_cases.create_qa_dataset_entry import CreateQaDatasetEntryUseCase
from src.application.evaluation.use_cases.list_qa_dataset_entries import ListQaDatasetEntriesUseCase
from src.application.ingestion.use_cases.delete_document import DeleteDocumentUseCase
from src.application.ingestion.use_cases.ingest_uploaded_file import IngestUploadedFileUseCase
from src.application.ingestion.use_cases.reindex_document import ReindexDocumentUseCase
from src.services.project_service import ProjectService
from src.services.rag_service import RAGService


@lru_cache(maxsize=1)
def get_ragcraft_app() -> RAGCraftApp:
    """Single application instance (DB init, shared services)."""
    return RAGCraftApp()


def get_project_service(
    app: Annotated[RAGCraftApp, Depends(get_ragcraft_app)],
) -> ProjectService:
    return app.project_service


def get_rag_service(
    app: Annotated[RAGCraftApp, Depends(get_ragcraft_app)],
) -> RAGService:
    return app.rag_service


def get_create_qa_dataset_entry_use_case(
    app: Annotated[RAGCraftApp, Depends(get_ragcraft_app)],
) -> CreateQaDatasetEntryUseCase:
    return CreateQaDatasetEntryUseCase(qa_dataset_service=app.qa_dataset_service)


def get_list_qa_dataset_entries_use_case(
    app: Annotated[RAGCraftApp, Depends(get_ragcraft_app)],
) -> ListQaDatasetEntriesUseCase:
    return ListQaDatasetEntriesUseCase(qa_dataset_service=app.qa_dataset_service)


def get_build_benchmark_export_artifacts_use_case() -> BuildBenchmarkExportArtifactsUseCase:
    return BuildBenchmarkExportArtifactsUseCase()


def get_ingest_uploaded_file_use_case(
    app: Annotated[RAGCraftApp, Depends(get_ragcraft_app)],
) -> IngestUploadedFileUseCase:
    return IngestUploadedFileUseCase(
        ingestion_service=app.ingestion_service,
        docstore_service=app.docstore_service,
        vectorstore_service=app.vectorstore_service,
        invalidate_project_chain=app.invalidate_project_chain,
    )


def get_reindex_document_use_case(
    app: Annotated[RAGCraftApp, Depends(get_ragcraft_app)],
) -> ReindexDocumentUseCase:
    return ReindexDocumentUseCase(
        ingestion_service=app.ingestion_service,
        docstore_service=app.docstore_service,
        vectorstore_service=app.vectorstore_service,
        invalidate_project_chain=app.invalidate_project_chain,
    )


def get_delete_document_use_case(
    app: Annotated[RAGCraftApp, Depends(get_ragcraft_app)],
) -> DeleteDocumentUseCase:
    return DeleteDocumentUseCase(
        docstore_service=app.docstore_service,
        vectorstore_service=app.vectorstore_service,
        invalidate_project_chain=app.invalidate_project_chain,
    )
