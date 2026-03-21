"""
FastAPI dependency providers.

Wiring uses :func:`get_backend_composition` (single process-wide graph) and
:class:`~src.app.ragcraft_app.RAGCraftApp` as the UI façade over that graph — same services as
Streamlit, shared ``QueryLogService`` and lazy ``RAGService``.

Use-case imports stay deferred inside getters where needed so ``import apps.api.dependencies`` does
not load FAISS / LangChain (keeps ``/health`` importable in minimal environments).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException

from src.services.project_service import ProjectService


@lru_cache(maxsize=1)
def get_backend_composition() -> Any:
    from src.composition import build_backend_composition

    return build_backend_composition()


@lru_cache(maxsize=1)
def get_ragcraft_app() -> Any:
    from src.app.ragcraft_app import RAGCraftApp

    return RAGCraftApp(backend=get_backend_composition())


def get_project_service(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> ProjectService:
    return app.project_service


def get_request_user_id(
    x_user_id: Annotated[
        str | None,
        Header(
            alias="X-User-Id",
            description=(
                "Required workspace user id. Extension point: replace with a verified principal "
                "from OAuth/JWT without changing route paths."
            ),
        ),
    ] = None,
) -> str:
    if x_user_id is None or not str(x_user_id).strip():
        raise HTTPException(
            status_code=400,
            detail="Missing or empty X-User-Id header.",
        )
    return str(x_user_id).strip()


def get_list_projects_use_case(
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> Any:
    from src.application.projects.use_cases.list_projects import ListProjectsUseCase

    return ListProjectsUseCase(project_service=project_service)


def get_create_project_use_case(
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> Any:
    from src.application.projects.use_cases.create_project import CreateProjectUseCase

    return CreateProjectUseCase(project_service=project_service)


def get_list_project_documents_use_case(
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> Any:
    from src.application.projects.use_cases.list_project_documents import (
        ListProjectDocumentsUseCase,
    )

    return ListProjectDocumentsUseCase(project_service=project_service)


def get_rag_service(app: Annotated[Any, Depends(get_ragcraft_app)]) -> Any:
    return app.rag_service


def get_ask_question_use_case(rag: Annotated[Any, Depends(get_rag_service)]) -> Any:
    return rag.ask_question_use_case


def get_inspect_pipeline_use_case(rag: Annotated[Any, Depends(get_rag_service)]) -> Any:
    return rag.inspect_pipeline_use_case


def get_preview_summary_recall_use_case(rag: Annotated[Any, Depends(get_rag_service)]) -> Any:
    return rag.preview_summary_recall_use_case


def get_create_qa_dataset_entry_use_case(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> Any:
    from src.application.evaluation.use_cases.create_qa_dataset_entry import (
        CreateQaDatasetEntryUseCase,
    )

    return CreateQaDatasetEntryUseCase(qa_dataset_service=app.qa_dataset_service)


def get_list_qa_dataset_entries_use_case(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> Any:
    from src.application.evaluation.use_cases.list_qa_dataset_entries import (
        ListQaDatasetEntriesUseCase,
    )

    return ListQaDatasetEntriesUseCase(qa_dataset_service=app.qa_dataset_service)


def get_build_benchmark_export_artifacts_use_case() -> Any:
    from src.application.evaluation.use_cases.build_benchmark_export_artifacts import (
        BuildBenchmarkExportArtifactsUseCase,
    )

    return BuildBenchmarkExportArtifactsUseCase()


def get_run_manual_evaluation_use_case(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> Any:
    from src.application.evaluation.use_cases.run_manual_evaluation import RunManualEvaluationUseCase

    return RunManualEvaluationUseCase(
        project_service=app.project_service,
        rag_service=app.rag_service,
        evaluation_service=app.evaluation_service,
    )


def get_run_gold_qa_dataset_evaluation_use_case(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> Any:
    from src.application.evaluation.use_cases.list_qa_dataset_entries import (
        ListQaDatasetEntriesUseCase,
    )
    from src.application.evaluation.use_cases.run_gold_qa_dataset_evaluation import (
        RunGoldQaDatasetEvaluationUseCase,
    )

    return RunGoldQaDatasetEvaluationUseCase(
        list_qa_dataset_entries=ListQaDatasetEntriesUseCase(qa_dataset_service=app.qa_dataset_service),
        project_service=app.project_service,
        rag_service=app.rag_service,
        evaluation_service=app.evaluation_service,
    )


def get_update_qa_dataset_entry_use_case(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> Any:
    from src.application.evaluation.use_cases.update_qa_dataset_entry import (
        UpdateQaDatasetEntryUseCase,
    )

    return UpdateQaDatasetEntryUseCase(qa_dataset_service=app.qa_dataset_service)


def get_delete_qa_dataset_entry_use_case(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> Any:
    from src.application.evaluation.use_cases.delete_qa_dataset_entry import (
        DeleteQaDatasetEntryUseCase,
    )

    return DeleteQaDatasetEntryUseCase(qa_dataset_service=app.qa_dataset_service)


def get_generate_qa_dataset_use_case(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> Any:
    from src.application.evaluation.use_cases.generate_qa_dataset import GenerateQaDatasetUseCase

    return GenerateQaDatasetUseCase(
        qa_dataset_service=app.qa_dataset_service,
        qa_dataset_generation_service=app.qa_dataset_generation_service,
    )


def get_list_retrieval_query_logs_use_case(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> Any:
    from src.application.evaluation.use_cases.list_retrieval_query_logs import (
        ListRetrievalQueryLogsUseCase,
    )

    return ListRetrievalQueryLogsUseCase(query_log_service=app.query_log_service)


def get_ingest_uploaded_file_use_case(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> Any:
    from src.application.ingestion.use_cases.ingest_uploaded_file import IngestUploadedFileUseCase

    return IngestUploadedFileUseCase(
        ingestion_service=app.ingestion_service,
        docstore_service=app.docstore_service,
        vectorstore_service=app.vectorstore_service,
        invalidate_project_chain=app.invalidate_project_chain,
    )


def get_reindex_document_use_case(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> Any:
    from src.application.ingestion.use_cases.reindex_document import ReindexDocumentUseCase

    return ReindexDocumentUseCase(
        ingestion_service=app.ingestion_service,
        docstore_service=app.docstore_service,
        vectorstore_service=app.vectorstore_service,
        invalidate_project_chain=app.invalidate_project_chain,
    )


def get_delete_document_use_case(
    app: Annotated[Any, Depends(get_ragcraft_app)],
) -> Any:
    from src.application.ingestion.use_cases.delete_document import DeleteDocumentUseCase

    return DeleteDocumentUseCase(
        docstore_service=app.docstore_service,
        vectorstore_service=app.vectorstore_service,
        invalidate_project_chain=app.invalidate_project_chain,
    )
