"""Shared FastAPI + dependency overrides for reliability flow tests."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.dto.ingestion import DocumentReplacementSummary, IngestDocumentResult
from domain.common.ingestion_diagnostics import IngestionDiagnostics
from domain.projects.documents.stored_multimodal_asset import StoredMultimodalAsset
from domain.projects.project import Project
from domain.rag.pipeline_latency import PipelineLatency
from domain.rag.rag_response import RAGResponse
from interfaces.http.dependencies import (
    get_ask_question_use_case,
    get_create_project_use_case,
    get_ingest_uploaded_file_use_case,
    get_resolve_project_use_case,
)
from interfaces.http.main import create_app


class _CallableUseCase:
    def __init__(self, fn: Callable[..., Any]) -> None:
        self._fn = fn

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self._fn(*args, **kwargs)


class _FakeProjectWorkspace:
    def get_project(self, user_id: str, project_id: str) -> Project:
        return Project(user_id=user_id, project_id=project_id)


class _FakeResolveProjectUseCase:
    def __init__(self, inner: _FakeProjectWorkspace) -> None:
        self._inner = inner

    def execute(self, user_id: str, project_id: str) -> Project:
        return self._inner.get_project(user_id, project_id)


def _ingest_result() -> IngestDocumentResult:
    return IngestDocumentResult(
        raw_assets=[
            StoredMultimodalAsset.from_mapping(
                {
                    "doc_id": "rel-1",
                    "user_id": "u",
                    "project_id": "p",
                    "source_file": "note.txt",
                    "content_type": "text",
                    "raw_content": "body",
                    "summary": "sum",
                    "metadata": {},
                }
            )
        ],
        replacement_info=DocumentReplacementSummary(
            existing_doc_ids=[], deleted_vectors=0, deleted_assets=0
        ),
        diagnostics=IngestionDiagnostics(total_ms=1.0, generated_assets=1),
    )


@pytest.fixture
def chat_flow_client() -> Iterator[tuple[TestClient, FastAPI]]:
    """Resolve project + ask only (minimal chat surface)."""
    app = create_app()
    workspace = _FakeProjectWorkspace()
    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        workspace
    )
    app.dependency_overrides[get_ask_question_use_case] = lambda: _CallableUseCase(
        lambda project, question, *a, **k: RAGResponse(
            question=question,
            answer="reliability-chat-answer",
            confidence=0.9,
            latency=PipelineLatency(total_ms=10.0),
        )
    )
    with TestClient(app) as tc:
        yield tc, app
    app.dependency_overrides.clear()


@pytest.fixture
def e2e_flow_client() -> Iterator[tuple[TestClient, FastAPI]]:
    """Create project → ingest → ask (HTTP-only, stubbed use cases)."""
    app = create_app()
    workspace = _FakeProjectWorkspace()
    app.dependency_overrides[get_create_project_use_case] = lambda: _CallableUseCase(
        lambda uid, pid: None
    )
    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        workspace
    )
    app.dependency_overrides[get_ingest_uploaded_file_use_case] = lambda: _CallableUseCase(
        lambda cmd: _ingest_result()
    )
    app.dependency_overrides[get_ask_question_use_case] = lambda: _CallableUseCase(
        lambda project, question, *a, **k: RAGResponse(
            question=question,
            answer="reliability-e2e-answer",
            confidence=0.91,
            latency=PipelineLatency(total_ms=11.0),
        )
    )
    with TestClient(app) as tc:
        yield tc, app
    app.dependency_overrides.clear()
