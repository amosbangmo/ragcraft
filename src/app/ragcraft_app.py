"""
In-process backend adapter over :class:`~src.composition.BackendApplicationContainer`.

Used by :class:`~src.frontend_gateway.in_process.InProcessBackendClient` when Streamlit runs **without**
uvicorn (default local dev). **FastAPI** does not import this module; it uses the same container via
``apps.api.dependencies``. New UI code should use :class:`~src.frontend_gateway.protocol.BackendClient`,
not ``RAGCraftApp`` directly. See ``docs/migration/ragcraftapp-deprecation.md`` and ``ARCHITECTURE_TARGET.md``.
"""

from __future__ import annotations

from datetime import datetime

from src.composition import (
    BackendComposition,
    BackendApplicationContainer,
    build_backend,
    build_backend_composition,
)
from src.application.settings.dtos import (
    EffectiveRetrievalSettingsView,
    GetEffectiveRetrievalSettingsQuery,
    UpdateProjectRetrievalSettingsCommand,
)
from src.domain.project_settings import ProjectSettings
from src.application.evaluation.dtos import (
    CreateQaDatasetEntryCommand,
    DeleteQaDatasetEntryCommand,
    GenerateQaDatasetCommand,
    ListQaDatasetEntriesQuery,
    ListRetrievalQueryLogsQuery,
    RunGoldQaDatasetEvaluationCommand,
    RunManualEvaluationCommand,
    UpdateQaDatasetEntryCommand,
)
from src.application.ingestion.dtos import (
    DeleteDocumentCommand,
    DeleteDocumentResult,
    IngestDocumentResult,
    IngestUploadedFileCommand,
    ReindexDocumentCommand,
)
from src.application.ingestion.use_cases.replace_document_assets import (
    replace_document_assets_for_reingest,
)
from src.application.evaluation.benchmark_export_dtos import (
    BenchmarkExportArtifacts,
    BuildBenchmarkExportCommand,
)
from src.domain.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from src.domain.benchmark_result import BenchmarkResult
from src.domain.retrieval_filters import RetrievalFilters
from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.domain.pipeline_payloads import PipelineBuildResult

from src.infrastructure.caching.process_project_chain_cache import (
    get_default_process_project_chain_cache,
)
from src.ui.streamlit_project_chain_session_cache import (
    get_cached_chain,
    set_cached_chain,
    invalidate_all_project_chains,
    invalidate_project_chain as _invalidate_streamlit_session_chain,
)


def _invalidate_process_and_streamlit_chain_cache(project_id: str) -> None:
    """Evict shared process cache then Streamlit session cache (UI process only)."""
    get_default_process_project_chain_cache().drop(project_id)
    _invalidate_streamlit_session_chain(project_id)


class RAGCraftApp:
    """
    In-process wrapper around :class:`BackendApplicationContainer` for the Streamlit process.

    Ingest/delete/reindex entrypoints delegate to the same container use cases as the HTTP API and
    return application DTOs (:class:`~src.application.ingestion.dtos.IngestDocumentResult`,
    :class:`~src.application.ingestion.dtos.DeleteDocumentResult`).

    Prefer constructing via ``application_container=`` when sharing a process-wide graph (FastAPI);
    the no-arg constructor builds a fresh composition (typical Streamlit session).
    """

    def __init__(
        self,
        backend: BackendComposition | None = None,
        *,
        application_container: BackendApplicationContainer | None = None,
    ) -> None:
        if backend is not None and application_container is not None:
            raise ValueError("Pass at most one of backend and application_container")

        if application_container is not None:
            self._container = application_container
        else:
            resolved_backend = backend or build_backend_composition()
            self._container = build_backend(
                backend=resolved_backend,
                invalidate_chain_key=_invalidate_process_and_streamlit_chain_cache,
            )

        self._backend = self._container.backend

        # Mutable attributes (tests and callers may replace instances); keep in sync with container services.
        self.auth_service = self._container.auth_service
        self.project_service = self._container.project_service
        self.ingestion_service = self._container.ingestion_service
        self.vectorstore_service = self._container.vectorstore_service
        self.evaluation_service = self._container.evaluation_service
        self.chat_service = self._container.chat_service
        self.docstore_service = self._container.docstore_service
        self.reranking_service = self._container.reranking_service
        self.qa_dataset_service = self._container.qa_dataset_service
        self.qa_dataset_generation_service = self._container.qa_dataset_generation_service
        self.project_settings_service = self._container.project_settings_service
        self.retrieval_settings_service = self._container.retrieval_settings_service
        self.query_log_service = self._container.query_log_service

    @property
    def project_settings_repository(self) -> ProjectSettingsRepositoryPort:
        return self.project_settings_service

    def get_effective_retrieval_settings(
        self, user_id: str, project_id: str
    ) -> EffectiveRetrievalSettingsView:
        return self._container.settings_get_effective_retrieval_use_case.execute(
            GetEffectiveRetrievalSettingsQuery(user_id=user_id, project_id=project_id)
        )

    def update_project_retrieval_settings(
        self, command: UpdateProjectRetrievalSettingsCommand
    ) -> ProjectSettings:
        return self._container.settings_update_project_retrieval_use_case.execute(command)

    @property
    def rag_service(self):
        return self._backend.rag_service

    @property
    def retrieval_comparison_service(self):
        return self._backend.retrieval_comparison_service

    def get_current_user_record(self):
        return self.auth_service.get_current_user_record()

    def format_created_at(self, created_at: str | None) -> str:
        return self.auth_service.format_created_at(created_at)

    def update_profile(
        self,
        *,
        user_id: str,
        new_username: str,
        new_display_name: str,
    ) -> tuple[bool, str]:
        return self.auth_service.update_profile(
            user_id=user_id,
            new_username=new_username,
            new_display_name=new_display_name,
        )

    def change_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
        confirm_new_password: str,
    ) -> tuple[bool, str]:
        return self.auth_service.change_password(
            user_id=user_id,
            current_password=current_password,
            new_password=new_password,
            confirm_new_password=confirm_new_password,
        )

    def save_avatar(self, user_id: str, uploaded_file) -> tuple[bool, str]:
        return self.auth_service.save_avatar(user_id, uploaded_file)

    def remove_avatar(self, user_id: str) -> tuple[bool, str]:
        return self.auth_service.remove_avatar(user_id)

    def delete_account(self, *, user_id: str, current_password: str) -> tuple[bool, str]:
        return self.auth_service.delete_account(
            user_id=user_id,
            current_password=current_password,
        )

    def get_project(self, user_id: str, project_id: str):
        return self.project_service.get_project(user_id, project_id)

    def create_project(self, user_id: str, project_id: str):
        return self.project_service.create_project(user_id, project_id)

    def list_projects(self, user_id: str):
        return self.project_service.list_projects(user_id)

    def retrieval_preset_label_for_project(self, user_id: str, project_id: str) -> str:
        return self.project_settings_service.preset_label_for_project(user_id, project_id)

    def list_retrieval_query_logs(
        self,
        *,
        user_id: str,
        project_id: str,
        since_iso: str | None = None,
        until_iso: str | None = None,
        last_n: int | None = None,
    ) -> list[dict]:
        return self._container.evaluation_list_retrieval_query_logs_use_case.execute(
            ListRetrievalQueryLogsQuery(
                user_id=user_id,
                project_id=project_id,
                since_iso=since_iso,
                until_iso=until_iso,
                last_n=last_n,
            )
        )

    def list_project_documents(self, user_id: str, project_id: str) -> list[str]:
        return self.project_service.list_project_documents(user_id, project_id)

    def get_project_document_details(self, user_id: str, project_id: str) -> list[dict]:
        project = self.get_project(user_id, project_id)
        documents = self.list_project_documents(user_id, project_id)

        details = []

        for doc_name in documents:
            file_path = project.path / doc_name

            asset_count = self.docstore_service.count_assets_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=doc_name,
            )

            asset_stats = self.docstore_service.get_asset_stats_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=doc_name,
            )

            details.append(
                {
                    "name": doc_name,
                    "project_id": project_id,
                    "path": str(file_path),
                    "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
                    "asset_count": asset_count,
                    "text_count": int(asset_stats.get("text_count", 0)),
                    "table_count": int(asset_stats.get("table_count", 0)),
                    "image_count": int(asset_stats.get("image_count", 0)),
                    "latest_ingested_at": asset_stats.get("latest_ingested_at"),
                }
            )

        return details

    def get_document_assets(self, user_id: str, project_id: str, source_file: str) -> list[dict]:
        return self.docstore_service.list_assets_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
        )

    def get_or_build_project_chain(self, user_id: str, project_id: str):
        project = self.get_project(user_id, project_id)
        project_key = project.project_id

        cached_object = get_cached_chain(project_key)

        if cached_object is not None:
            return cached_object

        cached_object = self.rag_service.build_chain(project)

        if cached_object is not None:
            set_cached_chain(project_key, cached_object)

        return cached_object

    def invalidate_project_chain(self, user_id: str, project_id: str) -> None:
        self._container.invalidate_project_chain(user_id, project_id)
        # Always evict the Streamlit session layer too when this façade is used (including a shared
        # FastAPI-built container whose ``invalidate_chain_key`` only targets the process cache).
        _invalidate_streamlit_session_chain(project_id)

    def invalidate_all_project_chains(self):
        invalidate_all_project_chains()

    def replace_document_assets(self, user_id: str, project_id: str, source_file: str) -> dict:
        project = self.get_project(user_id, project_id)
        return replace_document_assets_for_reingest(
            project=project,
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
            asset_repository=self.docstore_service,
            vector_index=self.vectorstore_service,
            invalidate_project_chain=self.invalidate_project_chain,
        )

    def delete_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> DeleteDocumentResult:
        project = self.get_project(user_id, project_id)
        return self._container.ingestion_delete_document_use_case.execute(
            DeleteDocumentCommand(project=project, source_file=source_file)
        )

    def ingest_uploaded_file(
        self, user_id: str, project_id: str, uploaded_file
    ) -> IngestDocumentResult:
        project = self.get_project(user_id, project_id)
        return self._container.ingestion_ingest_uploaded_file_use_case.execute(
            IngestUploadedFileCommand(project=project, uploaded_file=uploaded_file)
        )

    def reindex_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> IngestDocumentResult:
        project = self.get_project(user_id, project_id)
        return self._container.ingestion_reindex_document_use_case.execute(
            ReindexDocumentCommand(project=project, source_file=source_file)
        )

    def ask_question(
        self,
        user_id: str,
        project_id: str,
        question: str,
        chat_history=None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ):
        project = self.get_project(user_id, project_id)
        return self.rag_service.ask(
            project,
            question,
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

    def evaluate_manual_question(
        self,
        *,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> ManualEvaluationResult:
        return self._container.evaluation_run_manual_evaluation_use_case.execute(
            RunManualEvaluationCommand(
                user_id=user_id,
                project_id=project_id,
                question=question,
                expected_answer=expected_answer,
                expected_doc_ids=expected_doc_ids,
                expected_sources=expected_sources,
                enable_query_rewrite_override=enable_query_rewrite_override,
                enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
            )
        )

    def inspect_retrieval(
        self,
        user_id: str,
        project_id: str,
        question: str,
        chat_history=None,
        *,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict | None = None,
    ) -> PipelineBuildResult | None:
        project = self.get_project(user_id, project_id)
        return self.rag_service.inspect_pipeline(
            project,
            question,
            chat_history,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
            filters=filters,
            retrieval_settings=retrieval_settings,
        )

    def search_project_summaries(
        self,
        user_id: str,
        project_id: str,
        query: str,
        chat_history=None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ):
        project = self.get_project(user_id, project_id)
        return self.rag_service.preview_summary_recall(
            project,
            query,
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

    def compare_retrieval_modes(
        self,
        *,
        user_id: str,
        project_id: str,
        questions: list[str],
        enable_query_rewrite: bool,
    ) -> dict:
        project = self.get_project(user_id, project_id)
        return self.retrieval_comparison_service.compare(
            project=project,
            questions=questions,
            enable_query_rewrite=enable_query_rewrite,
        )

    def create_qa_dataset_entry(
        self,
        *,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ):
        return self._container.evaluation_create_qa_dataset_entry_use_case.execute(
            user_id=user_id,
            project_id=project_id,
            question=question,
            expected_answer=expected_answer,
            expected_doc_ids=expected_doc_ids,
            expected_sources=expected_sources,
        )

    def list_qa_dataset_entries(
        self,
        *,
        user_id: str,
        project_id: str,
    ):
        return self._container.evaluation_list_qa_dataset_entries_use_case.execute(
            ListQaDatasetEntriesQuery(user_id=user_id, project_id=project_id)
        )

    def update_qa_dataset_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ):
        return self._container.evaluation_update_qa_dataset_entry_use_case.execute(
            UpdateQaDatasetEntryCommand(
                entry_id=entry_id,
                user_id=user_id,
                project_id=project_id,
                question=question,
                expected_answer=expected_answer,
                expected_doc_ids=expected_doc_ids,
                expected_sources=expected_sources,
            )
        )

    def delete_qa_dataset_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
    ) -> bool:
        return self._container.evaluation_delete_qa_dataset_entry_use_case.execute(
            DeleteQaDatasetEntryCommand(
                entry_id=entry_id,
                user_id=user_id,
                project_id=project_id,
            )
        )

    def generate_qa_dataset_entries(
        self,
        *,
        user_id: str,
        project_id: str,
        num_questions: int,
        source_files: list[str] | None = None,
        generation_mode: str = "append",
    ) -> dict:
        return self._container.evaluation_generate_qa_dataset_use_case.execute(
            GenerateQaDatasetCommand(
                user_id=user_id,
                project_id=project_id,
                num_questions=num_questions,
                source_files=source_files,
                generation_mode=generation_mode,
            )
        )

    def evaluate_gold_qa_dataset(
        self,
        *,
        user_id: str,
        project_id: str,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
    ):
        return self._container.evaluation_run_gold_qa_dataset_evaluation_use_case.execute(
            RunGoldQaDatasetEvaluationCommand(
                user_id=user_id,
                project_id=project_id,
                enable_query_rewrite=enable_query_rewrite,
                enable_hybrid_retrieval=enable_hybrid_retrieval,
            )
        )

    def build_benchmark_export_artifacts(
        self,
        *,
        project_id: str,
        result: BenchmarkResult,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
        generated_at: datetime | None = None,
    ) -> BenchmarkExportArtifacts:
        """Build JSON/CSV/Markdown downloads; ``BenchmarkExportArtifacts.run_id`` mirrors ``result.run_id`` when set."""
        return self._container.evaluation_build_benchmark_export_artifacts_use_case.execute(
            BuildBenchmarkExportCommand(
                project_id=project_id,
                result=result,
                enable_query_rewrite=enable_query_rewrite,
                enable_hybrid_retrieval=enable_hybrid_retrieval,
                generated_at=generated_at,
            )
        )
