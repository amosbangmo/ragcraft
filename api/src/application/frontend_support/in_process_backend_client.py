"""In-process :class:`~application.frontend_support.backend_client_protocol.BackendClient` backed by :class:`~composition.BackendApplicationContainer`."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from application.dto.benchmark_export import BuildBenchmarkExportCommand
from application.dto.evaluation import (
    CreateQaDatasetEntryCommand,
    DeleteQaDatasetEntryCommand,
    GenerateQaDatasetCommand,
    ListQaDatasetEntriesQuery,
    ListRetrievalQueryLogsQuery,
    RunGoldQaDatasetEvaluationCommand,
    RunManualEvaluationCommand,
    UpdateQaDatasetEntryCommand,
)
from application.dto.ingestion import (
    DeleteDocumentCommand,
    IngestUploadedFileCommand,
    ReindexDocumentCommand,
)
from application.dto.settings import GetEffectiveRetrievalSettingsQuery
from application.dto.settings import (
    UpdateProjectRetrievalSettingsCommand as AppUpdateProjectRetrievalSettingsCommand,
)
from application.http.wire import retrieval_comparison_to_wire_dict
from components.shared.streamlit_project_chain_session_cache import (
    invalidate_project_chain as _invalidate_streamlit_session_chain,
)
from composition import BackendApplicationContainer
from domain.common.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from domain.evaluation.qa_dataset_entry import QADatasetEntry
from domain.projects.buffered_document_upload import BufferedDocumentUpload
from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.rag.rag_inspect_answer_run import RagInspectAnswerRun
from domain.rag.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec
from services.api_contract_models import UpdateProjectRetrievalSettingsCommand
from application.frontend_support.client_wire_mappers import (
    benchmark_result_to_wire,
    delete_document_result_to_wire,
    effective_retrieval_view_to_wire,
    ingest_document_result_to_wire,
    manual_evaluation_to_wire,
    project_settings_to_payload,
    qa_dataset_entry_to_wire,
    rag_response_to_rag_answer,
    retrieval_filters_to_domain,
    wire_benchmark_to_domain,
)
from services.evaluation_wire_models import BenchmarkResult


class InProcessBackendClient:
    def __init__(self, container: BackendApplicationContainer) -> None:
        self._container = container

    def init_chat_session(self, project_id: str) -> None:
        self._container.chat_transcript.init(project_id)

    def get_chat_messages(self) -> list[dict[str, Any]]:
        return self._container.chat_transcript.get_messages()

    def add_chat_user_message(self, content: str) -> None:
        self._container.chat_transcript.add_user_message(content)

    def add_chat_assistant_message(self, content: str) -> None:
        self._container.chat_transcript.add_assistant_message(content)

    def generate_answer_from_pipeline(
        self, *, project: Project, pipeline: PipelineBuildResult
    ) -> str:
        return self._container.chat_generate_answer_from_pipeline_use_case.execute(
            project=project, pipeline=pipeline
        )

    def evaluate_gold_qa_dataset_with_runner(
        self,
        *,
        entries: list[QADatasetEntry],
        pipeline_runner: Callable[[QADatasetEntry], RagInspectAnswerRun],
    ) -> BenchmarkResult:
        raw = self._container.evaluation_service.evaluate_gold_qa_dataset(
            entries=entries,
            pipeline_runner=pipeline_runner,
        )
        return benchmark_result_to_wire(raw)

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
        documents = self._container.projects_list_project_documents_use_case.execute(
            user_id, project_id
        )
        return self._container.projects_get_project_document_details_use_case.execute(
            user_id=user_id, project_id=project_id, document_names=documents
        )

    def get_document_assets(self, user_id: str, project_id: str, source_file: str) -> list[dict]:
        return self._container.projects_list_document_assets_for_source_use_case.execute(
            user_id=user_id, project_id=project_id, source_file=source_file
        )

    def delete_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> Any:
        project = self.get_project(user_id, project_id)
        result = self._container.ingestion_delete_document_use_case.execute(
            DeleteDocumentCommand(project=project, source_file=source_file)
        )
        return delete_document_result_to_wire(result)

    def ingest_uploaded_file(
        self, user_id: str, project_id: str, uploaded_file: Any
    ) -> Any:
        project = self.get_project(user_id, project_id)
        upload = (
            uploaded_file
            if isinstance(uploaded_file, BufferedDocumentUpload)
            else BufferedDocumentUpload.from_duck_typed(uploaded_file)
        )
        result = self._container.ingestion_ingest_uploaded_file_use_case.execute(
            IngestUploadedFileCommand(project=project, upload=upload)
        )
        return ingest_document_result_to_wire(result)

    def reindex_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> Any:
        project = self.get_project(user_id, project_id)
        result = self._container.ingestion_reindex_document_use_case.execute(
            ReindexDocumentCommand(project=project, source_file=source_file)
        )
        return ingest_document_result_to_wire(result)

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
        filters: Any | None = None,
        retrieval_settings: dict | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> Any:
        project = self._container.projects_resolve_project_use_case.execute(user_id, project_id)
        overrides = RetrievalSettingsOverrideSpec.from_optional_mapping(retrieval_settings)
        domain_filters = retrieval_filters_to_domain(filters)
        raw = self._container.chat_ask_question_use_case.execute(
            project,
            question,
            chat_history,
            filters=domain_filters,
            retrieval_overrides=overrides,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        return rag_response_to_rag_answer(raw)

    def get_effective_retrieval_settings(
        self, user_id: str, project_id: str
    ) -> Any:
        view = self._container.settings_get_effective_retrieval_use_case.execute(
            GetEffectiveRetrievalSettingsQuery(user_id=user_id, project_id=project_id)
        )
        return effective_retrieval_view_to_wire(view)

    def update_project_retrieval_settings(
        self, command: UpdateProjectRetrievalSettingsCommand
    ) -> Any:
        app_cmd = AppUpdateProjectRetrievalSettingsCommand(
            user_id=command.user_id,
            project_id=command.project_id,
            retrieval_preset=command.retrieval_preset,
            retrieval_advanced=command.retrieval_advanced,
            enable_query_rewrite=command.enable_query_rewrite,
            enable_hybrid_retrieval=command.enable_hybrid_retrieval,
        )
        ps = self._container.settings_update_project_retrieval_use_case.execute(app_cmd)
        return project_settings_to_payload(ps)

    def search_project_summaries(
        self,
        user_id: str,
        project_id: str,
        query: str,
        chat_history: Any = None,
        *,
        filters: Any | None = None,
        retrieval_settings: dict | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> Any:
        project = self._container.projects_resolve_project_use_case.execute(user_id, project_id)
        overrides = RetrievalSettingsOverrideSpec.from_optional_mapping(retrieval_settings)
        domain_filters = retrieval_filters_to_domain(filters)
        dto = self._container.chat_preview_summary_recall_use_case.execute(
            project,
            query,
            chat_history,
            filters=domain_filters,
            retrieval_overrides=overrides,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        return dto.to_dict() if dto is not None else None

    def inspect_retrieval(
        self,
        user_id: str,
        project_id: str,
        question: str,
        chat_history: Any = None,
        *,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
        filters: Any | None = None,
        retrieval_settings: dict | None = None,
    ) -> PipelineBuildResult | None:
        project = self._container.projects_resolve_project_use_case.execute(user_id, project_id)
        overrides = RetrievalSettingsOverrideSpec.from_optional_mapping(retrieval_settings)
        domain_filters = retrieval_filters_to_domain(filters)
        return self._container.chat_inspect_pipeline_use_case.execute(
            project,
            question,
            chat_history,
            filters=domain_filters,
            retrieval_overrides=overrides,
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
        result = self._container.chat_compare_retrieval_modes_use_case.execute(
            user_id=user_id,
            project_id=project_id,
            questions=questions,
            enable_query_rewrite=enable_query_rewrite,
        )
        return retrieval_comparison_to_wire_dict(result)

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
    ) -> Any:
        domain_result = self._container.evaluation_run_manual_evaluation_use_case.execute(
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
        return manual_evaluation_to_wire(domain_result)

    def evaluate_gold_qa_dataset(
        self,
        *,
        user_id: str,
        project_id: str,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
    ) -> BenchmarkResult:
        raw = self._container.evaluation_run_gold_qa_dataset_evaluation_use_case.execute(
            RunGoldQaDatasetEvaluationCommand(
                user_id=user_id,
                project_id=project_id,
                enable_query_rewrite=enable_query_rewrite,
                enable_hybrid_retrieval=enable_hybrid_retrieval,
            )
        )
        return benchmark_result_to_wire(raw)

    def build_benchmark_export_artifacts(
        self,
        *,
        project_id: str,
        result: BenchmarkResult,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
        generated_at: datetime | None = None,
    ) -> Any:
        domain_result = wire_benchmark_to_domain(result)
        return self._container.evaluation_build_benchmark_export_artifacts_use_case.execute(
            BuildBenchmarkExportCommand(
                project_id=project_id,
                result=domain_result,
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
        row = self._container.evaluation_create_qa_dataset_entry_use_case.execute(
            CreateQaDatasetEntryCommand(
                user_id=user_id,
                project_id=project_id,
                question=question,
                expected_answer=expected_answer,
                expected_doc_ids=expected_doc_ids,
                expected_sources=expected_sources,
            )
        )
        return qa_dataset_entry_to_wire(row)

    def list_qa_dataset_entries(self, *, user_id: str, project_id: str) -> Any:
        rows = self._container.evaluation_list_qa_dataset_entries_use_case.execute(
            ListQaDatasetEntriesQuery(user_id=user_id, project_id=project_id)
        )
        return [qa_dataset_entry_to_wire(e) for e in rows]

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
        row = self._container.evaluation_update_qa_dataset_entry_use_case.execute(
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
        return qa_dataset_entry_to_wire(row)

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
        result = self._container.evaluation_generate_qa_dataset_use_case.execute(
            GenerateQaDatasetCommand(
                user_id=user_id,
                project_id=project_id,
                num_questions=num_questions,
                source_files=source_files,
                generation_mode=generation_mode,
            )
        )
        return {
            "generation_mode": result.generation_mode,
            "deleted_existing_entries": result.deleted_existing_entries,
            "created_entries": [qa_dataset_entry_to_wire(e) for e in result.created_entries],
            "skipped_duplicates": list(result.skipped_duplicates),
            "requested_questions": result.requested_questions,
            "raw_generated_count": result.raw_generated_count,
        }

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
