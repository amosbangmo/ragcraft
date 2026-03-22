"""In-process :class:`~src.frontend_gateway.protocol.BackendClient` backed by :class:`~src.app.ragcraft_app.RAGCraftApp`."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.app.ragcraft_app import RAGCraftApp
from src.application.settings.dtos import (
    EffectiveRetrievalSettingsView,
    UpdateProjectRetrievalSettingsCommand,
)
from src.domain.benchmark_result import BenchmarkResult
from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project_settings import ProjectSettings
from src.domain.retrieval_filters import RetrievalFilters
from src.domain.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from src.application.ingestion.dtos import DeleteDocumentResult, IngestDocumentResult


class InProcessBackendClient:
    __slots__ = ("_app",)

    def __init__(self, app: RAGCraftApp) -> None:
        self._app = app

    @property
    def chat_service(self) -> Any:
        return self._app.chat_service

    @property
    def retrieval_settings_service(self) -> Any:
        return self._app.retrieval_settings_service

    @property
    def rag_service(self) -> Any:
        return self._app.rag_service

    @property
    def evaluation_service(self) -> Any:
        return self._app.evaluation_service

    @property
    def project_settings_repository(self) -> ProjectSettingsRepositoryPort:
        return self._app.project_settings_repository

    def get_current_user_record(self) -> Any:
        return self._app.get_current_user_record()

    def format_created_at(self, created_at: str | None) -> str:
        return self._app.format_created_at(created_at)

    def update_profile(
        self,
        *,
        user_id: str,
        new_username: str,
        new_display_name: str,
    ) -> tuple[bool, str]:
        return self._app.update_profile(
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
        return self._app.change_password(
            user_id=user_id,
            current_password=current_password,
            new_password=new_password,
            confirm_new_password=confirm_new_password,
        )

    def save_avatar(self, user_id: str, uploaded_file: Any) -> tuple[bool, str]:
        return self._app.save_avatar(user_id, uploaded_file)

    def remove_avatar(self, user_id: str) -> tuple[bool, str]:
        return self._app.remove_avatar(user_id)

    def delete_account(self, *, user_id: str, current_password: str) -> tuple[bool, str]:
        return self._app.delete_account(user_id=user_id, current_password=current_password)

    def list_projects(self, user_id: str) -> list[str]:
        return self._app.list_projects(user_id)

    def create_project(self, user_id: str, project_id: str) -> Any:
        return self._app.create_project(user_id, project_id)

    def get_project(self, user_id: str, project_id: str) -> Any:
        return self._app.get_project(user_id, project_id)

    def retrieval_preset_label_for_project(self, user_id: str, project_id: str) -> str:
        return self._app.retrieval_preset_label_for_project(user_id, project_id)

    def list_project_documents(self, user_id: str, project_id: str) -> list[str]:
        return self._app.list_project_documents(user_id, project_id)

    def get_project_document_details(self, user_id: str, project_id: str) -> list[dict]:
        return self._app.get_project_document_details(user_id, project_id)

    def get_document_assets(self, user_id: str, project_id: str, source_file: str) -> list[dict]:
        return self._app.get_document_assets(user_id, project_id, source_file)

    def delete_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> DeleteDocumentResult:
        return self._app.delete_project_document(user_id, project_id, source_file)

    def ingest_uploaded_file(
        self, user_id: str, project_id: str, uploaded_file: Any
    ) -> IngestDocumentResult:
        return self._app.ingest_uploaded_file(user_id, project_id, uploaded_file)

    def reindex_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> IngestDocumentResult:
        return self._app.reindex_project_document(user_id, project_id, source_file)

    def invalidate_project_chain(self, user_id: str, project_id: str) -> None:
        return self._app.invalidate_project_chain(user_id, project_id)

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
        return self._app.ask_question(
            user_id,
            project_id,
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
        return self._app.get_effective_retrieval_settings(user_id, project_id)

    def update_project_retrieval_settings(
        self, command: UpdateProjectRetrievalSettingsCommand
    ) -> ProjectSettings:
        return self._app.update_project_retrieval_settings(command)

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
        return self._app.search_project_summaries(
            user_id,
            project_id,
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
        return self._app.inspect_retrieval(
            user_id,
            project_id,
            question,
            chat_history,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
            filters=filters,
            retrieval_settings=retrieval_settings,
        )

    def compare_retrieval_modes(
        self,
        *,
        user_id: str,
        project_id: str,
        questions: list[str],
        enable_query_rewrite: bool,
    ) -> dict:
        return self._app.compare_retrieval_modes(
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
        return self._app.evaluate_manual_question(
            user_id=user_id,
            project_id=project_id,
            question=question,
            expected_answer=expected_answer,
            expected_doc_ids=expected_doc_ids,
            expected_sources=expected_sources,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

    def evaluate_gold_qa_dataset(
        self,
        *,
        user_id: str,
        project_id: str,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
    ) -> Any:
        return self._app.evaluate_gold_qa_dataset(
            user_id=user_id,
            project_id=project_id,
            enable_query_rewrite=enable_query_rewrite,
            enable_hybrid_retrieval=enable_hybrid_retrieval,
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
        return self._app.build_benchmark_export_artifacts(
            project_id=project_id,
            result=result,
            enable_query_rewrite=enable_query_rewrite,
            enable_hybrid_retrieval=enable_hybrid_retrieval,
            generated_at=generated_at,
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
        return self._app.create_qa_dataset_entry(
            user_id=user_id,
            project_id=project_id,
            question=question,
            expected_answer=expected_answer,
            expected_doc_ids=expected_doc_ids,
            expected_sources=expected_sources,
        )

    def list_qa_dataset_entries(self, *, user_id: str, project_id: str) -> Any:
        return self._app.list_qa_dataset_entries(user_id=user_id, project_id=project_id)

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
        return self._app.update_qa_dataset_entry(
            entry_id=entry_id,
            user_id=user_id,
            project_id=project_id,
            question=question,
            expected_answer=expected_answer,
            expected_doc_ids=expected_doc_ids,
            expected_sources=expected_sources,
        )

    def delete_qa_dataset_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
    ) -> bool:
        return self._app.delete_qa_dataset_entry(
            entry_id=entry_id,
            user_id=user_id,
            project_id=project_id,
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
        return self._app.generate_qa_dataset_entries(
            user_id=user_id,
            project_id=project_id,
            num_questions=num_questions,
            source_files=source_files,
            generation_mode=generation_mode,
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
        return self._app.list_retrieval_query_logs(
            user_id=user_id,
            project_id=project_id,
            since_iso=since_iso,
            until_iso=until_iso,
            last_n=last_n,
        )
