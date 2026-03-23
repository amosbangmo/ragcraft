"""Backend client that calls the FastAPI app over HTTP with ``Authorization: Bearer``."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from application.dto.ingestion import DeleteDocumentResult, IngestDocumentResult
from application.dto.settings import (
    EffectiveRetrievalSettingsView,
    UpdateProjectRetrievalSettingsCommand,
)
from domain.evaluation.benchmark_result import BenchmarkResult, coerce_benchmark_result
from domain.evaluation.manual_evaluation_result import manual_evaluation_result_from_plain_dict
from domain.evaluation.qa_dataset_entry import QADatasetEntry
from domain.projects.project import Project
from domain.projects.project_settings import ProjectSettings
from domain.rag.pipeline_latency import PipelineLatency
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.rag.rag_response import RAGResponse
from domain.rag.retrieval_filters import RetrievalFilters
from services.http_payloads import (
    benchmark_export_artifacts_from_api_dict,
    delete_document_result_from_api_dict,
    effective_retrieval_view_from_api_dict,
    ingest_document_result_from_api_dict,
    qa_dataset_entry_from_api_dict,
    qa_generate_result_from_api_dict,
)
from services.http_transport import HttpTransport
from services.stubs import http_client_chat_service, http_client_project_settings_repository


def _streamlit_access_token_supplier() -> str:
    try:
        import streamlit as st

        from infrastructure.auth.auth_service import AuthService

        return str(st.session_state.get(AuthService.SESSION_ACCESS_TOKEN_KEY, "") or "").strip()
    except Exception:
        return ""


def _format_created_at(created_at: str | None) -> str:
    if not created_at:
        return "-"
    try:
        dt = datetime.fromisoformat(created_at)
        return dt.strftime("%d %b %Y, %H:%M")
    except Exception:
        return created_at


def _filters_body(filters: RetrievalFilters | None) -> dict[str, Any] | None:
    if filters is None or filters.is_empty():
        return None
    d = filters.to_dict()
    return {
        "source_files": d.get("source_files") or [],
        "content_types": d.get("content_types") or [],
        "page_numbers": d.get("page_numbers") or [],
        "page_start": d.get("page_start"),
        "page_end": d.get("page_end"),
    }


def _chat_pipeline_body(
    *,
    project_id: str,
    question: str,
    chat_history: Any,
    filters: RetrievalFilters | None,
    retrieval_settings: dict | None,
    enable_query_rewrite_override: bool | None,
    enable_hybrid_retrieval_override: bool | None,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "question": question,
        "chat_history": list(chat_history or []),
        "filters": _filters_body(filters),
        "retrieval_settings": retrieval_settings,
        "enable_query_rewrite_override": enable_query_rewrite_override,
        "enable_hybrid_retrieval_override": enable_hybrid_retrieval_override,
    }


class HttpBackendClient:
    __slots__ = ("_access_token_supplier", "_t", "base_url", "connect_timeout", "read_timeout")

    def __init__(
        self,
        *,
        base_url: str,
        connect_timeout: float = 10.0,
        read_timeout: float = 300.0,
        transport: httpx.BaseTransport | None = None,
        access_token_supplier: Callable[[], str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.connect_timeout = float(connect_timeout)
        self.read_timeout = float(read_timeout)
        self._access_token_supplier = access_token_supplier or _streamlit_access_token_supplier
        self._t = HttpTransport(
            base_url=self.base_url,
            connect_timeout=self.connect_timeout,
            read_timeout=self.read_timeout,
            transport=transport,
        )

    def _bearer(self) -> str:
        return self._access_token_supplier().strip()

    def close(self) -> None:
        self._t.close()

    def init_chat_session(self, project_id: str) -> None:
        http_client_chat_service().init(project_id)

    def get_chat_messages(self) -> list[dict[str, Any]]:
        return http_client_chat_service().get_messages()

    def add_chat_user_message(self, content: str) -> None:
        http_client_chat_service().add_user_message(content)

    def add_chat_assistant_message(self, content: str) -> None:
        http_client_chat_service().add_assistant_message(content)

    def generate_answer_from_pipeline(
        self, *, project: Project, pipeline: PipelineBuildResult
    ) -> str:
        raise NotImplementedError(
            "generate_answer_from_pipeline is not exposed over HTTP; use POST /evaluation/manual "
            "or the in-process backend client."
        )

    def evaluate_gold_qa_dataset_with_runner(
        self,
        *,
        entries: list[QADatasetEntry],
        pipeline_runner: Any,
    ) -> BenchmarkResult:
        raise NotImplementedError(
            "evaluate_gold_qa_dataset_with_runner is not exposed over HTTP; use POST /evaluation/dataset/run "
            "or the in-process backend client."
        )

    @property
    def project_settings_repository(self) -> Any:
        return http_client_project_settings_repository()

    def get_current_user_record(self) -> Any:
        import streamlit as st

        uid = st.session_state.get("user_id")
        if not uid:
            return None
        return self._t.request_json("GET", "/users/me", bearer_token=self._bearer())

    def format_created_at(self, created_at: str | None) -> str:
        return _format_created_at(created_at)

    def update_profile(
        self,
        *,
        user_id: str,
        new_username: str,
        new_display_name: str,
    ) -> tuple[bool, str]:
        data = self._t.request_json(
            "PATCH",
            "/users/me",
            bearer_token=self._bearer(),
            json_body={"username": new_username, "display_name": new_display_name},
        )
        return bool(data.get("success")), str(data.get("message") or "")

    def change_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
        confirm_new_password: str,
    ) -> tuple[bool, str]:
        data = self._t.request_json(
            "POST",
            "/users/me/password",
            bearer_token=self._bearer(),
            json_body={
                "current_password": current_password,
                "new_password": new_password,
                "confirm_new_password": confirm_new_password,
            },
        )
        return bool(data.get("success")), str(data.get("message") or "")

    def save_avatar(self, user_id: str, uploaded_file: Any) -> tuple[bool, str]:
        name = getattr(uploaded_file, "name", "avatar") or "avatar"
        buf = uploaded_file.getbuffer()
        ctype = getattr(uploaded_file, "type", None) or "application/octet-stream"
        data = self._t.request_json(
            "POST",
            "/users/me/avatar",
            bearer_token=self._bearer(),
            files={"file": (name, buf, ctype)},
        )
        return bool(data.get("success")), str(data.get("message") or "")

    def remove_avatar(self, user_id: str) -> tuple[bool, str]:
        data = self._t.request_json("DELETE", "/users/me/avatar", bearer_token=self._bearer())
        return bool(data.get("success")), str(data.get("message") or "")

    def delete_account(self, *, user_id: str, current_password: str) -> tuple[bool, str]:
        data = self._t.request_json(
            "DELETE",
            "/users/me",
            bearer_token=self._bearer(),
            json_body={"current_password": current_password},
        )
        return bool(data.get("success")), str(data.get("message") or "")

    def list_projects(self, user_id: str) -> list[str]:
        data = self._t.request_json("GET", "/projects", bearer_token=self._bearer())
        return list(data.get("projects") or [])

    def create_project(self, user_id: str, project_id: str) -> Any:
        self._t.request_json(
            "POST",
            "/projects",
            bearer_token=self._bearer(),
            json_body={"project_id": project_id},
        )
        return self.get_project(user_id, project_id)

    def get_project(self, user_id: str, project_id: str) -> Any:
        data = self._t.request_json(
            "GET", f"/projects/{quote(project_id)}", bearer_token=self._bearer()
        )
        return Project(user_id=str(data["user_id"]), project_id=str(data["project_id"]))

    def retrieval_preset_label_for_project(self, user_id: str, project_id: str) -> str:
        data = self._t.request_json(
            "GET",
            f"/projects/{quote(project_id)}/retrieval-preset-label",
            bearer_token=self._bearer(),
        )
        return str(data.get("label") or "")

    def list_project_documents(self, user_id: str, project_id: str) -> list[str]:
        data = self._t.request_json(
            "GET",
            f"/projects/{quote(project_id)}/documents",
            bearer_token=self._bearer(),
        )
        return list(data.get("documents") or [])

    def get_project_document_details(self, user_id: str, project_id: str) -> list[dict]:
        data = self._t.request_json(
            "GET",
            f"/projects/{quote(project_id)}/documents/details",
            bearer_token=self._bearer(),
        )
        return list(data.get("documents") or [])

    def get_document_assets(self, user_id: str, project_id: str, source_file: str) -> list[dict]:
        sf = quote(source_file, safe="")
        data = self._t.request_json(
            "GET",
            f"/projects/{quote(project_id)}/documents/{sf}/assets",
            bearer_token=self._bearer(),
        )
        return list(data.get("assets") or [])

    def delete_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> DeleteDocumentResult:
        sf = quote(source_file, safe="")
        data = self._t.request_json(
            "DELETE",
            f"/projects/{quote(project_id)}/documents/{sf}",
            bearer_token=self._bearer(),
        )
        return delete_document_result_from_api_dict(data)

    def ingest_uploaded_file(
        self, user_id: str, project_id: str, uploaded_file: Any
    ) -> IngestDocumentResult:
        name = getattr(uploaded_file, "name", "upload") or "upload"
        buf = uploaded_file.getbuffer()
        ctype = getattr(uploaded_file, "type", None) or "application/octet-stream"
        data = self._t.request_json(
            "POST",
            f"/projects/{quote(project_id)}/documents/ingest",
            bearer_token=self._bearer(),
            files={"file": (name, buf, ctype)},
        )
        return ingest_document_result_from_api_dict(data)

    def reindex_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> IngestDocumentResult:
        sf = quote(source_file, safe="")
        data = self._t.request_json(
            "POST",
            f"/projects/{quote(project_id)}/documents/{sf}/reindex",
            bearer_token=self._bearer(),
        )
        return ingest_document_result_from_api_dict(data)

    def invalidate_project_chain(self, user_id: str, project_id: str) -> None:
        self._t.request_json(
            "POST",
            f"/projects/{quote(project_id)}/retrieval-cache/invalidate",
            bearer_token=self._bearer(),
            json_body={},
        )

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
        body = _chat_pipeline_body(
            project_id=project_id,
            question=question,
            chat_history=chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        data = self._t.request_json(
            "POST", "/chat/ask", bearer_token=self._bearer(), json_body=body
        )
        if data.get("status") == "no_pipeline":
            return None
        lat_raw = data.get("latency")
        latency = PipelineLatency.from_dict(lat_raw) if isinstance(lat_raw, dict) else None
        return RAGResponse(
            question=str(data.get("question") or ""),
            answer=str(data.get("answer") or ""),
            source_documents=list(data.get("source_documents") or []),
            raw_assets=list(data.get("raw_assets") or []),
            prompt_sources=list(data.get("prompt_sources") or []),
            confidence=float(data.get("confidence") or 0.0),
            latency=latency,
        )

    def get_effective_retrieval_settings(
        self, user_id: str, project_id: str
    ) -> EffectiveRetrievalSettingsView:
        data = self._t.request_json(
            "GET",
            f"/projects/{quote(project_id)}/retrieval-settings",
            bearer_token=self._bearer(),
        )
        return effective_retrieval_view_from_api_dict(data)

    def update_project_retrieval_settings(
        self, command: UpdateProjectRetrievalSettingsCommand
    ) -> ProjectSettings:
        # Alias imported as _PutCmd is same class; accept either
        cmd: UpdateProjectRetrievalSettingsCommand = command
        body = {
            "retrieval_preset": cmd.retrieval_preset,
            "retrieval_advanced": cmd.retrieval_advanced,
            "enable_query_rewrite": cmd.enable_query_rewrite,
            "enable_hybrid_retrieval": cmd.enable_hybrid_retrieval,
        }
        data = self._t.request_json(
            "PUT",
            f"/projects/{quote(cmd.project_id)}/retrieval-settings",
            bearer_token=self._bearer(),
            json_body=body,
        )
        view = effective_retrieval_view_from_api_dict(data)
        return view.preferences

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
        body = _chat_pipeline_body(
            project_id=project_id,
            question=query,
            chat_history=chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        data = self._t.request_json(
            "POST",
            "/chat/pipeline/preview-summary-recall",
            bearer_token=self._bearer(),
            json_body=body,
        )
        if data.get("status") != "ok":
            return None
        return data.get("preview")

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
    ) -> Any:
        body = _chat_pipeline_body(
            project_id=project_id,
            question=question,
            chat_history=chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        data = self._t.request_json(
            "POST", "/chat/pipeline/inspect", bearer_token=self._bearer(), json_body=body
        )
        if data.get("status") != "ok":
            return None
        pl = data.get("pipeline")
        return pl if isinstance(pl, dict) else None

    def compare_retrieval_modes(
        self,
        *,
        user_id: str,
        project_id: str,
        questions: list[str],
        enable_query_rewrite: bool,
    ) -> dict:
        data = self._t.request_json(
            "POST",
            "/chat/retrieval/compare",
            bearer_token=self._bearer(),
            json_body={
                "project_id": project_id,
                "questions": questions,
                "enable_query_rewrite": enable_query_rewrite,
            },
        )
        return {
            "summary": data.get("summary") or {},
            "rows": list(data.get("rows") or []),
        }

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
        data = self._t.request_json(
            "POST",
            "/evaluation/manual",
            bearer_token=self._bearer(),
            json_body={
                "project_id": project_id,
                "question": question,
                "expected_answer": expected_answer,
                "expected_doc_ids": list(expected_doc_ids or []),
                "expected_sources": list(expected_sources or []),
                "enable_query_rewrite_override": enable_query_rewrite_override,
                "enable_hybrid_retrieval_override": enable_hybrid_retrieval_override,
            },
        )
        return manual_evaluation_result_from_plain_dict(data)

    def evaluate_gold_qa_dataset(
        self,
        *,
        user_id: str,
        project_id: str,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
    ) -> Any:
        data = self._t.request_json(
            "POST",
            "/evaluation/dataset/run",
            bearer_token=self._bearer(),
            json_body={
                "project_id": project_id,
                "enable_query_rewrite": enable_query_rewrite,
                "enable_hybrid_retrieval": enable_hybrid_retrieval,
            },
        )
        bench = coerce_benchmark_result(data)
        if bench is None:
            raise ValueError("Benchmark API returned an unreadable payload.")
        return bench

    def build_benchmark_export_artifacts(
        self,
        *,
        project_id: str,
        result: BenchmarkResult,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
        generated_at: datetime | None = None,
    ) -> Any:
        ga: str | None = None
        if generated_at is not None:
            ga = (
                generated_at.isoformat()
                if hasattr(generated_at, "isoformat")
                else str(generated_at)
            )
        data = self._t.request_json(
            "POST",
            "/evaluation/export/benchmark",
            json_body={
                "project_id": project_id,
                "enable_query_rewrite": enable_query_rewrite,
                "enable_hybrid_retrieval": enable_hybrid_retrieval,
                "result": result.to_dict(),
                "generated_at": ga,
            },
            send_authorization=False,
        )
        return benchmark_export_artifacts_from_api_dict(data)

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
        data = self._t.request_json(
            "POST",
            "/evaluation/dataset/entries",
            bearer_token=self._bearer(),
            json_body={
                "project_id": project_id,
                "question": question,
                "expected_answer": expected_answer,
                "expected_doc_ids": list(expected_doc_ids or []),
                "expected_sources": list(expected_sources or []),
            },
        )
        return qa_dataset_entry_from_api_dict(data)

    def list_qa_dataset_entries(self, *, user_id: str, project_id: str) -> Any:
        data = self._t.request_json(
            "GET",
            "/evaluation/dataset/entries",
            bearer_token=self._bearer(),
            params={"project_id": project_id},
        )
        return [qa_dataset_entry_from_api_dict(e) for e in (data.get("entries") or [])]

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
        data = self._t.request_json(
            "PUT",
            f"/evaluation/dataset/entries/{entry_id}",
            bearer_token=self._bearer(),
            json_body={
                "project_id": project_id,
                "question": question,
                "expected_answer": expected_answer,
                "expected_doc_ids": list(expected_doc_ids or []),
                "expected_sources": list(expected_sources or []),
            },
        )
        return qa_dataset_entry_from_api_dict(data)

    def delete_qa_dataset_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
    ) -> bool:
        self._t.request_json(
            "DELETE",
            f"/evaluation/dataset/entries/{entry_id}",
            bearer_token=self._bearer(),
            params={"project_id": project_id},
        )
        return True

    def generate_qa_dataset_entries(
        self,
        *,
        user_id: str,
        project_id: str,
        num_questions: int,
        source_files: list[str] | None = None,
        generation_mode: str = "append",
    ) -> dict:
        data = self._t.request_json(
            "POST",
            "/evaluation/dataset/generate",
            bearer_token=self._bearer(),
            json_body={
                "project_id": project_id,
                "num_questions": num_questions,
                "source_files": source_files,
                "generation_mode": generation_mode,
            },
        )
        return qa_generate_result_from_api_dict(data)

    def list_retrieval_query_logs(
        self,
        *,
        user_id: str,
        project_id: str,
        since_iso: str | None = None,
        until_iso: str | None = None,
        last_n: int | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {"project_id": project_id}
        if since_iso:
            params["since"] = since_iso
        if until_iso:
            params["until"] = until_iso
        if last_n is not None:
            params["limit"] = last_n
        data = self._t.request_json(
            "GET",
            "/evaluation/retrieval/logs",
            bearer_token=self._bearer(),
            params=params,
        )
        return list(data.get("entries") or [])
