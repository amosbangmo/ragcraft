"""
Frontend integration seam for backend capabilities (Streamlit today; Angular/SPA via HTTP).

Implementations: **HTTP** (:class:`~services.http_client.HttpBackendClient` → FastAPI; default)
or **in-process** (:class:`~services.in_process.InProcessBackendClient` →
:class:`~composition.BackendApplicationContainer`). Pages should depend only on this protocol,
:mod:`services.view_models`, and auth helpers — not on ``infrastructure.adapters`` or the composition root.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from application.dto.settings import (
    EffectiveRetrievalSettingsView,
    UpdateProjectRetrievalSettingsCommand,
)
from domain.evaluation.benchmark_result import BenchmarkResult
from domain.evaluation.manual_evaluation_result import ManualEvaluationResult
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.projects.project import Project
from domain.projects.project_settings import ProjectSettings
from domain.evaluation.qa_dataset_entry import QADatasetEntry
from domain.rag.rag_inspect_answer_run import RagInspectAnswerRun
from domain.rag.retrieval_filters import RetrievalFilters
from domain.common.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from application.dto.ingestion import DeleteDocumentResult, IngestDocumentResult


@runtime_checkable
class BackendClient(Protocol):
    """
    Minimal backend operations used by Streamlit pages today.

    Login, registration, and session display-name/avatar reads use
    :mod:`services.streamlit_auth` (HTTP mode calls ``/auth/login`` and ``/auth/register``).

    Chat transcript, preset merge, RAG answer generation, and gold-QA benchmarking are exposed as
    façade methods so pages do not reach adapter singletons directly.
    """

    def init_chat_session(self, project_id: str) -> None: ...

    def get_chat_messages(self) -> list[dict[str, Any]]: ...

    def add_chat_user_message(self, content: str) -> None: ...

    def add_chat_assistant_message(self, content: str) -> None: ...

    def generate_answer_from_pipeline(
        self, *, project: Project, pipeline: PipelineBuildResult
    ) -> str: ...

    def evaluate_gold_qa_dataset_with_runner(
        self,
        *,
        entries: list[QADatasetEntry],
        pipeline_runner: Callable[[QADatasetEntry], RagInspectAnswerRun],
    ) -> BenchmarkResult: ...

    @property
    def project_settings_repository(self) -> ProjectSettingsRepositoryPort: ...

    def get_current_user_record(self) -> Any: ...

    def format_created_at(self, created_at: str | None) -> str: ...

    def update_profile(
        self,
        *,
        user_id: str,
        new_username: str,
        new_display_name: str,
    ) -> tuple[bool, str]: ...

    def change_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
        confirm_new_password: str,
    ) -> tuple[bool, str]: ...

    def save_avatar(self, user_id: str, uploaded_file: Any) -> tuple[bool, str]: ...

    def remove_avatar(self, user_id: str) -> tuple[bool, str]: ...

    def delete_account(self, *, user_id: str, current_password: str) -> tuple[bool, str]: ...

    def list_projects(self, user_id: str) -> list[str]: ...

    def create_project(self, user_id: str, project_id: str) -> Any: ...

    def get_project(self, user_id: str, project_id: str) -> Any: ...

    def retrieval_preset_label_for_project(self, user_id: str, project_id: str) -> str: ...

    def list_project_documents(self, user_id: str, project_id: str) -> list[str]: ...

    def get_project_document_details(self, user_id: str, project_id: str) -> list[dict]: ...

    def get_document_assets(self, user_id: str, project_id: str, source_file: str) -> list[dict]: ...

    def delete_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> DeleteDocumentResult: ...

    def ingest_uploaded_file(
        self, user_id: str, project_id: str, uploaded_file: Any
    ) -> IngestDocumentResult: ...

    def reindex_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> IngestDocumentResult: ...

    def invalidate_project_chain(self, user_id: str, project_id: str) -> None: ...

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
    ) -> Any: ...

    def get_effective_retrieval_settings(
        self, user_id: str, project_id: str
    ) -> EffectiveRetrievalSettingsView: ...

    def update_project_retrieval_settings(
        self, command: UpdateProjectRetrievalSettingsCommand
    ) -> ProjectSettings: ...

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
    ) -> Any: ...

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
    ) -> PipelineBuildResult | None: ...

    def compare_retrieval_modes(
        self,
        *,
        user_id: str,
        project_id: str,
        questions: list[str],
        enable_query_rewrite: bool,
    ) -> dict: ...

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
    ) -> ManualEvaluationResult: ...

    def evaluate_gold_qa_dataset(
        self,
        *,
        user_id: str,
        project_id: str,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
    ) -> Any: ...

    def build_benchmark_export_artifacts(
        self,
        *,
        project_id: str,
        result: BenchmarkResult,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
        generated_at: datetime | None = None,
    ) -> Any: ...

    def create_qa_dataset_entry(
        self,
        *,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ) -> Any: ...

    def list_qa_dataset_entries(self, *, user_id: str, project_id: str) -> Any: ...

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
    ) -> Any: ...

    def delete_qa_dataset_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
    ) -> bool: ...

    def generate_qa_dataset_entries(
        self,
        *,
        user_id: str,
        project_id: str,
        num_questions: int,
        source_files: list[str] | None = None,
        generation_mode: str = "append",
    ) -> dict: ...

    def list_retrieval_query_logs(
        self,
        *,
        user_id: str,
        project_id: str,
        since_iso: str | None = None,
        until_iso: str | None = None,
        last_n: int | None = None,
    ) -> list[dict]: ...
