"""In-process :class:`~src.frontend_gateway.protocol.BackendClient` backed by :class:`~src.composition.BackendApplicationContainer`."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.application.evaluation.benchmark_export_dtos import BuildBenchmarkExportCommand
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
from src.application.settings.dtos import (
    EffectiveRetrievalSettingsView,
    GetEffectiveRetrievalSettingsQuery,
    UpdateProjectRetrievalSettingsCommand,
)
from src.composition import BackendApplicationContainer
from src.domain.benchmark_result import BenchmarkResult
from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.qa_dataset_entry import QADatasetEntry
from src.domain.project_settings import ProjectSettings
from src.domain.retrieval_filters import RetrievalFilters
from src.domain.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from src.ui.streamlit_project_chain_session_cache import (
    invalidate_project_chain as _invalidate_streamlit_session_chain,
)


class InProcessBackendClient:
    def __init__(self, container: BackendApplicationContainer) -> None:
        self._container = container

    def init_chat_session(self, project_id: str) -> None:
        self._container.chat_service.init(project_id)

    def get_chat_messages(self) -> list[dict[str, Any]]:
        return self._container.chat_service.get_messages()

    def add_chat_user_message(self, content: str) -> None:
        self._container.chat_service.add_user_message(content)

    def add_chat_assistant_message(self, content: str) -> None:
        self._container.chat_service.add_assistant_message(content)

    def generate_answer_from_pipeline(self, *, project: Project, pipeline: PipelineBuildResult) -> str:
        return self._container.chat_generate_answer_from_pipeline_use_case.execute(
            project=project, pipeline=pipeline
        )

    def evaluate_gold_qa_dataset_with_runner(
        self,
        *,
        entries: list[QADatasetEntry],
        pipeline_runner: Callable[[QADatasetEntry], dict[str, Any]],
    ) -> BenchmarkResult:
        return self._container.evaluation_service.evaluate_gold_qa_dataset(
            entries=entries,
            pipeline_runner=pipeline_runner,
        )

    @property
    def project_settings_repository(self) -> ProjectSettingsRepositoryPort:
        return self._container.project_settings_repository

    def get_current_user_record(self) -> Any:
        return self._container.auth_service.get_current_user_record()

    def format_created_at(self, created_at: str | None) -> str:
        return self._container.auth_service.format_created_at(created_at)

    def update_profile(
        self,
        *,
        user_id: str,
        new_username: str,
        new_display_name: str,
    ) -> tuple[bool, str]:
        return self._container.auth_service.update_profile(
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
        return self._container.auth_service.change_password(
            user_id=user_id,
            current_password=current_password,
            new_password=new_password,
            confirm_new_password=confirm_new_password,
        )

    def save_avatar(self, user_id: str, uploaded_file: Any) -> tuple[bool, str]:
        return self._container.auth_service.save_avatar(user_id, uploaded_file)

    def remove_avatar(self, user_id: str) -> tuple[bool, str]:
        return self._container.auth_service.remove_avatar(user_id)

    def delete_account(self, *, user_id: str, current_password: str) -> tuple[bool, str]:
        return self._container.auth_service.delete_account(
            user_id=user_id,
            current_password=current_password,
        )

    def list_projects(self, user_id: str) -> list[str]:
        return self._container.projects_list_projects_use_case.execute(user_id)

    def create_project(self, user_id: str, project_id: str) -> Any:
        return self._container.projects_create_project_use_case.execute(user_id, project_id)

    def get_project(self, user_id: str, project_id: str) -> Any:
        return self._container.projects_resolve_project_use_case.execute(user_id, project_id)

    def retrieval_preset_label_for_project(self, user_id: str, project_id: str) -> str:
        return self._container.projects_get_retrieval_preset_label_use_case.execute(
            user_id=user_id, project_id=project_id
        )

    def list_project_documents(self, user_id: str, project_id: str) -> list[str]:
        return self._container.projects_list_project_documents_use_case.execute(user_id, project_id)

    def get_project_document_details(self, user_id: str, project_id: str) -> list[dict]:
        documents = self._container.projects_list_project_documents_use_case.execute(user_id, project_id)
        return self._container.projects_get_project_document_details_use_case.execute(
            user_id=user_id, project_id=project_id, document_names=documents
        )

    def get_document_assets(self, user_id: str, project_id: str, source_file: str) -> list[dict]:
        return self._container.projects_list_document_assets_for_source_use_case.execute(
            user_id=user_id, project_id=project_id, source_file=source_file
        )

    def delete_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> DeleteDocumentResult:
        project = self.get_project(user_id, project_id)
        return self._container.ingestion_delete_document_use_case.execute(
            DeleteDocumentCommand(project=project, source_file=source_file)
        )

    def ingest_uploaded_file(
        self, user_id: str, project_id: str, uploaded_file: Any
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

    def invalidate_project_chain(self, user_id: str, project_id: str) -> None:
        self._container.invalidate_project_chain(user_id, project_id)
        _invalidate_streamlit_session_chain(project_id)

    def ask_question(
        self,
        user_id: str,
        project_id: str,
        question: str,
        chat_history: Any = None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> Any:
        project = self._container.projects_resolve_project_use_case.execute(user_id, project_id)
        return self._container.chat_ask_question_use_case.execute(
            project,
            question,
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

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

    def search_project_summaries(
        self,
        user_id: str,
        project_id: str,
        query: str,
        chat_history: Any = None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> Any:
        project = self._container.projects_resolve_project_use_case.execute(user_id, project_id)
        return self._container.chat_preview_summary_recall_use_case.execute(
            project,
            query,
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

    def inspect_retrieval(
        self,
        user_id: str,
        project_id: str,
        question: str,
        chat_history: Any = None,
        *,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict | None = None,
    ) -> PipelineBuildResult | None:
        project = self._container.projects_resolve_project_use_case.execute(user_id, project_id)
        return self._container.chat_inspect_pipeline_use_case.execute(
            project,
            question,
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
        return self._container.chat_compare_retrieval_modes_use_case.execute(
            user_id=user_id,
            project_id=project_id,
            questions=questions,
            enable_query_rewrite=enable_query_rewrite,
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

    def evaluate_gold_qa_dataset(
        self,
        *,
        user_id: str,
        project_id: str,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
    ) -> Any:
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
    ) -> Any:
        return self._container.evaluation_build_benchmark_export_artifacts_use_case.execute(
            BuildBenchmarkExportCommand(
                project_id=project_id,
                result=result,
                enable_query_rewrite=enable_query_rewrite,
                enable_hybrid_retrieval=enable_hybrid_retrieval,
                generated_at=generated_at,
            )
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
    ) -> Any:
        return self._container.evaluation_create_qa_dataset_entry_use_case.execute(
            CreateQaDatasetEntryCommand(
                user_id=user_id,
                project_id=project_id,
                question=question,
                expected_answer=expected_answer,
                expected_doc_ids=expected_doc_ids,
                expected_sources=expected_sources,
            )
        )

    def list_qa_dataset_entries(self, *, user_id: str, project_id: str) -> Any:
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
    ) -> Any:
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
