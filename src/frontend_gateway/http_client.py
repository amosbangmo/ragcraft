"""Backend client that calls the FastAPI app over HTTP (``X-User-Id`` on every request)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from src.application.settings.dtos import UpdateProjectRetrievalSettingsCommand
from src.domain.benchmark_result import BenchmarkResult, coerce_benchmark_result
from src.domain.manual_evaluation_result import manual_evaluation_result_from_plain_dict
from src.domain.project import Project
from src.domain.project_settings import ProjectSettings
from src.domain.qa_dataset_entry import QADatasetEntry
from src.domain.rag_response import RAGResponse
from src.domain.retrieval_filters import RetrievalFilters
from src.application.settings.dtos import EffectiveRetrievalSettingsView
from src.application.ingestion.dtos import DeleteDocumentResult, IngestDocumentResult
from src.frontend_gateway.http_payloads import (
    benchmark_export_artifacts_from_api_dict,
    delete_document_result_from_api_dict,
    effective_retrieval_view_from_api_dict,
    ingest_document_result_from_api_dict,
    qa_dataset_entry_from_api_dict,
    qa_generate_result_from_api_dict,
)
from src.frontend_gateway.http_transport import HttpTransport
from src.frontend_gateway.stubs import (
    http_client_chat_service,
    http_client_evaluation_service,
    http_client_project_settings_repository,
    http_client_rag_service,
    http_client_retrieval_settings_service,
)


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
    user_id: str,
    project_id: str,
    question: str,
    chat_history: Any,
    filters: RetrievalFilters | None,
    retrieval_settings: dict | None,
    enable_query_rewrite_override: bool | None,
    enable_hybrid_retrieval_override: bool | None,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "project_id": project_id,
        "question": question,
        "chat_history": list(chat_history or []),
        "filters": _filters_body(filters),
        "retrieval_settings": retrieval_settings,
        "enable_query_rewrite_override": enable_query_rewrite_override,
        "enable_hybrid_retrieval_override": enable_hybrid_retrieval_override,
    }


class HttpBackendClient:
    __slots__ = ("_t", "base_url", "connect_timeout", "read_timeout")

    def __init__(
        self,
        *,
        base_url: str,
        connect_timeout: float = 10.0,
        read_timeout: float = 300.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.connect_timeout = float(connect_timeout)
        self.read_timeout = float(read_timeout)
        self._t = HttpTransport(
            base_url=self.base_url,
            connect_timeout=self.connect_timeout,
            read_timeout=self.read_timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._t.close()

    @property
    def chat_service(self) -> Any:
        return http_client_chat_service()

    @property
    def retrieval_settings_service(self) -> Any:
        return http_client_retrieval_settings_service()

    @property
    def rag_service(self) -> Any:
        return http_client_rag_service()

    @property
    def evaluation_service(self) -> Any:
        return http_client_evaluation_service()

    @property
    def project_settings_repository(self) -> Any:
        return http_client_project_settings_repository()

    def get_current_user_record(self) -> Any:
        import streamlit as st

        uid = st.session_state.get("user_id")
        if not uid:
            return None
        return self._t.request_json("GET", "/users/me", user_id=str(uid))

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
            user_id=user_id,
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
            user_id=user_id,
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
            user_id=user_id,
            files={"file": (name, buf, ctype)},
        )
        return bool(data.get("success")), str(data.get("message") or "")

    def remove_avatar(self, user_id: str) -> tuple[bool, str]:
        data = self._t.request_json("DELETE", "/users/me/avatar", user_id=user_id)
        return bool(data.get("success")), str(data.get("message") or "")

    def delete_account(self, *, user_id: str, current_password: str) -> tuple[bool, str]:
        data = self._t.request_json(
            "DELETE",
            "/users/me",
            user_id=user_id,
            json_body={"current_password": current_password},
        )
        return bool(data.get("success")), str(data.get("message") or "")

    def list_projects(self, user_id: str) -> list[str]:
        data = self._t.request_json("GET", "/projects", user_id=user_id)
        return list(data.get("projects") or [])

    def create_project(self, user_id: str, project_id: str) -> Any:
        self._t.request_json(
            "POST",
            "/projects",
            user_id=user_id,
            json_body={"project_id": project_id},
        )
        return self.get_project(user_id, project_id)

    def get_project(self, user_id: str, project_id: str) -> Any:
        data = self._t.request_json("GET", f"/projects/{quote(project_id)}", user_id=user_id)
        return Project(user_id=str(data["user_id"]), project_id=str(data["project_id"]))

    def retrieval_preset_label_for_project(self, user_id: str, project_id: str) -> str:
        data = self._t.request_json(
            "GET",
            f"/projects/{quote(project_id)}/retrieval-preset-label",
            user_id=user_id,
        )
        return str(data.get("label") or "")

    def list_project_documents(self, user_id: str, project_id: str) -> list[str]:
        data = self._t.request_json(
            "GET",
            f"/projects/{quote(project_id)}/documents",
            user_id=user_id,
        )
        return list(data.get("documents") or [])

    def get_project_document_details(self, user_id: str, project_id: str) -> list[dict]:
        data = self._t.request_json(
            "GET",
            f"/projects/{quote(project_id)}/documents/details",
            user_id=user_id,
        )
        return list(data.get("documents") or [])

    def get_document_assets(self, user_id: str, project_id: str, source_file: str) -> list[dict]:
        sf = quote(source_file, safe="")
        data = self._t.request_json(
            "GET",
            f"/projects/{quote(project_id)}/documents/{sf}/assets",
            user_id=user_id,
        )
        return list(data.get("assets") or [])

    def delete_project_document(
        self, user_id: str, project_id: str, source_file: str
    ) -> DeleteDocumentResult:
        sf = quote(source_file, safe="")
        data = self._t.request_json(
            "DELETE",
            f"/projects/{quote(project_id)}/documents/{sf}",
            user_id=user_id,
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
            user_id=user_id,
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
            user_id=user_id,
        )
        return ingest_document_result_from_api_dict(data)

    def invalidate_project_chain(self, user_id: str, project_id: str) -> None:
        self._t.request_json(
            "POST",
            f"/projects/{quote(project_id)}/retrieval-cache/invalidate",
            user_id=user_id,
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
            user_id=user_id,
            project_id=project_id,
            question=question,
            chat_history=chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        data = self._t.request_json("POST", "/chat/ask", user_id=user_id, json_body=body)
        if data.get("status") == "no_pipeline":
            return None
        return RAGResponse(
            question=str(data.get("question") or ""),
            answer=str(data.get("answer") or ""),
            source_documents=list(data.get("source_documents") or []),
            raw_assets=list(data.get("raw_assets") or []),
            prompt_sources=list(data.get("prompt_sources") or []),
            confidence=float(data.get("confidence") or 0.0),
            latency=data.get("latency"),
        )

    def get_effective_retrieval_settings(
        self, user_id: str, project_id: str
    ) -> EffectiveRetrievalSettingsView:
        data = self._t.request_json(
            "GET",
            f"/projects/{quote(project_id)}/retrieval-settings",
            user_id=user_id,
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
            user_id=cmd.user_id,
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
            user_id=user_id,
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
            user_id=user_id,
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
            user_id=user_id,
            project_id=project_id,
            question=question,
            chat_history=chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        data = self._t.request_json("POST", "/chat/pipeline/inspect", user_id=user_id, json_body=body)
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
            user_id=user_id,
            json_body={
                "user_id": user_id,
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
            user_id=user_id,
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
            user_id=user_id,
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
            ga = generated_at.isoformat() if hasattr(generated_at, "isoformat") else str(generated_at)
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
            send_user_header=False,
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
            user_id=user_id,
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
            user_id=user_id,
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
            user_id=user_id,
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
            user_id=user_id,
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
            user_id=user_id,
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
            user_id=user_id,
            params=params,
        )
        return list(data.get("entries") or [])
