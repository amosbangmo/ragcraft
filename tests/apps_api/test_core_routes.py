"""
FastAPI route coverage with dependency overrides (no full ``build_backend`` / unstructured).

Exercises happy paths and representative failures: missing identity header, validation,
:class:`~src.core.exceptions.RAGCraftError` mapping, and :class:`ValueError` / :class:`FileNotFoundError`.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.dependencies import (
    get_ask_question_use_case,
    get_build_benchmark_export_artifacts_use_case,
    get_create_project_use_case,
    get_ingest_uploaded_file_use_case,
    get_inspect_pipeline_use_case,
    get_list_project_documents_use_case,
    get_list_projects_use_case,
    get_resolve_project_use_case,
    get_run_gold_qa_dataset_evaluation_use_case,
    get_run_manual_evaluation_use_case,
)
from apps.api.main import create_app
from src.application.evaluation.use_cases.build_benchmark_export_artifacts import (
    BuildBenchmarkExportArtifactsUseCase,
)
from src.application.ingestion.dtos import IngestDocumentResult
from src.core.exceptions import DomainError, LLMServiceError, VectorStoreError
from src.domain.benchmark_result import BenchmarkResult, BenchmarkRow, BenchmarkSummary
from src.domain.ingestion_diagnostics import IngestionDiagnostics
from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.rag_response import RAGResponse


def _uid_header(user_id: str = "test-user-api") -> dict[str, str]:
    return {"X-User-Id": user_id}


class _FakeProjectService:
    """Minimal stand-in for :class:`~src.services.project_service.ProjectService`."""

    def __init__(
        self,
        *,
        project: Project | None = None,
        get_project_hook: Callable[[str, str], Project] | None = None,
    ) -> None:
        self._default = project
        self._get_project_hook = get_project_hook

    def get_project(self, user_id: str, project_id: str) -> Project:
        if self._get_project_hook is not None:
            return self._get_project_hook(user_id, project_id)
        if self._default is not None:
            return self._default
        return Project(user_id=user_id, project_id=project_id)


class _FakeResolveProjectUseCase:
    """Mirrors :class:`~src.application.projects.use_cases.resolve_project.ResolveProjectUseCase` for tests."""

    def __init__(self, svc: _FakeProjectService) -> None:
        self._svc = svc

    def execute(self, user_id: str, project_id: str) -> Project:
        return self._svc.get_project(user_id, project_id)


class _CallableUseCase:
    def __init__(self, fn: Callable[..., Any]) -> None:
        self._fn = fn

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self._fn(*args, **kwargs)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def override_app() -> Iterator[tuple[TestClient, FastAPI]]:
    app = create_app()
    with TestClient(app) as tc:
        yield tc, app
    app.dependency_overrides.clear()


def test_health_returns_ok(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_version_returns_service_and_version_strings(client: TestClient) -> None:
    r = client.get("/version")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("service"), str) and body["service"]
    assert isinstance(body.get("version"), str) and body["version"]


def test_projects_missing_x_user_id_returns_canonical_400(client: TestClient) -> None:
    r = client.get("/projects")
    assert r.status_code == 400
    err = r.json()
    assert err.get("code") == "http_400"
    assert err.get("category") == "transport"


def test_projects_list_and_create_happy_path(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    class _List:
        def execute(self, user_id: str) -> list[str]:
            assert user_id == "alice"
            return ["alpha", "beta"]

    class _Create:
        def execute(self, user_id: str, project_id: str) -> None:
            assert user_id == "alice"
            assert project_id == "new-proj"

    app.dependency_overrides[get_list_projects_use_case] = lambda: _List()
    app.dependency_overrides[get_create_project_use_case] = lambda: _Create()

    r = tc.get("/projects", headers=_uid_header("alice"))
    assert r.status_code == 200
    assert r.json() == {"projects": ["alpha", "beta"]}

    c = tc.post(
        "/projects",
        headers=_uid_header("alice"),
        json={"project_id": "new-proj"},
    )
    assert c.status_code == 201
    assert c.json() == {"project_id": "new-proj"}


def test_projects_create_validation_error_422(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app
    app.dependency_overrides[get_create_project_use_case] = lambda: _CallableUseCase(lambda *a, **k: None)
    r = tc.post(
        "/projects",
        headers=_uid_header(),
        json={"project_id": ""},
    )
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") == "request_validation_failed"


def test_projects_create_extra_field_forbidden_422(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app
    app.dependency_overrides[get_create_project_use_case] = lambda: _CallableUseCase(lambda *a, **k: None)
    r = tc.post(
        "/projects",
        headers=_uid_header(),
        json={"project_id": "ok", "unexpected": 1},
    )
    assert r.status_code == 422


def test_project_documents_happy_path(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    class _ListDocs:
        def execute(self, user_id: str, project_id: str) -> list[str]:
            assert user_id == "u1"
            assert project_id == "demo"
            return ["a.pdf", "b.pdf"]

    app.dependency_overrides[get_list_project_documents_use_case] = lambda: _ListDocs()
    r = tc.get(
        "/projects/demo/documents",
        headers=_uid_header("u1"),
    )
    assert r.status_code == 200
    assert r.json() == {"documents": ["a.pdf", "b.pdf"]}


def test_project_documents_missing_header_400(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app
    app.dependency_overrides[get_list_project_documents_use_case] = lambda: _CallableUseCase(lambda *a, **k: [])
    r = tc.get("/projects/demo/documents")
    assert r.status_code == 400


def test_document_ingest_happy_path(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    def _ingest(_cmd: Any) -> IngestDocumentResult:
        return IngestDocumentResult(
            raw_assets=[{"id": "1", "content_type": "text"}],
            replacement_info={"deleted_vectors": 0},
            diagnostics=IngestionDiagnostics(total_ms=12.0, generated_assets=1),
        )

    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        _FakeProjectService()
    )
    app.dependency_overrides[get_ingest_uploaded_file_use_case] = lambda: _CallableUseCase(_ingest)

    r = tc.post(
        "/projects/demo/documents/ingest",
        headers=_uid_header(),
        files={"file": ("hello.txt", b"hello world", "text/plain")},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data.get("raw_assets") or []) == 1
    assert data["diagnostics"]["total_ms"] == 12.0


def test_document_ingest_infrastructure_error_maps_to_503(
    override_app: tuple[TestClient, FastAPI],
) -> None:
    tc, app = override_app

    def _boom(_cmd: Any) -> IngestDocumentResult:
        raise VectorStoreError("internal", user_message="Vector layer unavailable.")

    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        _FakeProjectService()
    )
    app.dependency_overrides[get_ingest_uploaded_file_use_case] = lambda: _CallableUseCase(_boom)

    r = tc.post(
        "/projects/demo/documents/ingest",
        headers=_uid_header(),
        files={"file": ("x.txt", b"x", "text/plain")},
    )
    assert r.status_code == 503
    err = r.json()
    assert err.get("code") == "vector_store_unavailable"
    assert err.get("category") == "infrastructure"


def test_chat_ask_validation_without_loading_composition(
    override_app: tuple[TestClient, FastAPI],
) -> None:
    tc, app = override_app
    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        _FakeProjectService()
    )
    app.dependency_overrides[get_ask_question_use_case] = lambda: _CallableUseCase(lambda *a, **k: None)

    r = tc.post(
        "/chat/ask",
        headers=_uid_header(),
        json={"project_id": "demo", "question": ""},
    )
    assert r.status_code == 422


def test_chat_ask_answered_happy_path(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    def _answer(project: Any, question: str, *args: Any, **kwargs: Any) -> RAGResponse:
        assert question == "Why?"
        return RAGResponse(
            question=question,
            answer="Because.",
            confidence=0.5,
            latency={"total_ms": 1.0},
        )

    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        _FakeProjectService()
    )
    app.dependency_overrides[get_ask_question_use_case] = lambda: _CallableUseCase(_answer)

    r = tc.post(
        "/chat/ask",
        headers=_uid_header(),
        json={"project_id": "demo", "question": "Why?"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "answered"
    assert data["answer"] == "Because."
    assert data["confidence"] == 0.5


def test_chat_ask_no_pipeline_status(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app
    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        _FakeProjectService()
    )
    app.dependency_overrides[get_ask_question_use_case] = lambda: _CallableUseCase(lambda *a, **k: None)

    r = tc.post(
        "/chat/ask",
        headers=_uid_header(),
        json={"project_id": "demo", "question": "Anything"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "no_pipeline"
    assert data["answer"] == ""


def test_chat_ask_llm_service_error_maps_to_502(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    def _fail(*a: Any, **k: Any) -> None:
        raise LLMServiceError("upstream", user_message="Model failed.")

    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        _FakeProjectService()
    )
    app.dependency_overrides[get_ask_question_use_case] = lambda: _CallableUseCase(_fail)

    r = tc.post(
        "/chat/ask",
        headers=_uid_header(),
        json={"project_id": "demo", "question": "Q"},
    )
    assert r.status_code == 502
    err = r.json()
    assert err.get("code") == "llm_service_failed"
    assert err.get("category") == "infrastructure"


def test_chat_ask_domain_error_maps_to_400(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    def _domain_fail(*a: Any, **k: Any) -> None:
        raise DomainError("rule broken", user_message="Not allowed.")

    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        _FakeProjectService()
    )
    app.dependency_overrides[get_ask_question_use_case] = lambda: _CallableUseCase(_domain_fail)

    r = tc.post(
        "/chat/ask",
        headers=_uid_header(),
        json={"project_id": "demo", "question": "Q"},
    )
    assert r.status_code == 400
    err = r.json()
    assert err.get("code") == "domain_error"
    assert err.get("category") == "domain"


def test_pipeline_inspect_happy_path(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    def _pipe(*a: Any, **k: Any) -> PipelineBuildResult:
        r = PipelineBuildResult()
        r.question = "Inspect me"
        return r

    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        _FakeProjectService()
    )
    app.dependency_overrides[get_inspect_pipeline_use_case] = lambda: _CallableUseCase(_pipe)

    r = tc.post(
        "/chat/pipeline/inspect",
        headers=_uid_header(),
        json={"project_id": "demo", "question": "Inspect me"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["question"] == "Inspect me"
    assert isinstance(data.get("pipeline"), dict)


def test_pipeline_inspect_no_pipeline(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app
    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        _FakeProjectService()
    )
    app.dependency_overrides[get_inspect_pipeline_use_case] = lambda: _CallableUseCase(lambda *a, **k: None)

    r = tc.post(
        "/chat/pipeline/inspect",
        headers=_uid_header(),
        json={"project_id": "demo", "question": "Nope"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "no_pipeline"
    assert data["pipeline"] is None


def test_pipeline_inspect_vector_store_error_maps_to_503(
    override_app: tuple[TestClient, FastAPI],
) -> None:
    tc, app = override_app

    def _boom(*a: Any, **k: Any) -> None:
        raise VectorStoreError("bad index", user_message="Index failed.")

    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        _FakeProjectService()
    )
    app.dependency_overrides[get_inspect_pipeline_use_case] = lambda: _CallableUseCase(_boom)

    r = tc.post(
        "/chat/pipeline/inspect",
        headers=_uid_header(),
        json={"project_id": "demo", "question": "Q"},
    )
    assert r.status_code == 503
    assert r.json().get("code") == "vector_store_unavailable"


def test_evaluation_manual_happy_path(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    def _run(cmd: Any) -> ManualEvaluationResult:
        assert cmd.user_id == "u-eval"
        assert cmd.project_id == "demo"
        return ManualEvaluationResult(
            question=cmd.question,
            answer="A",
            expected_answer=cmd.expected_answer,
            confidence=0.9,
        )

    app.dependency_overrides[get_run_manual_evaluation_use_case] = lambda: _CallableUseCase(_run)

    r = tc.post(
        "/evaluation/manual",
        headers=_uid_header("u-eval"),
        json={"project_id": "demo", "question": "What?"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["question"] == "What?"
    assert data["answer"] == "A"
    assert data["confidence"] == 0.9


def test_evaluation_manual_missing_header_400(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app
    app.dependency_overrides[get_run_manual_evaluation_use_case] = lambda: _CallableUseCase(
        lambda *a, **k: ManualEvaluationResult(question="q", answer="a", expected_answer=None, confidence=0.0)
    )
    r = tc.post("/evaluation/manual", json={"project_id": "demo", "question": "Q"})
    assert r.status_code == 400


def test_evaluation_manual_llm_failure_502(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    def _raise(*a: Any, **k: Any) -> ManualEvaluationResult:
        raise LLMServiceError("x", user_message="judge down")

    app.dependency_overrides[get_run_manual_evaluation_use_case] = lambda: _CallableUseCase(_raise)

    r = tc.post(
        "/evaluation/manual",
        headers=_uid_header(),
        json={"project_id": "demo", "question": "Q"},
    )
    assert r.status_code == 502
    assert r.json().get("code") == "llm_service_failed"


def test_evaluation_dataset_run_happy_path(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    def _bench(cmd: Any) -> BenchmarkResult:
        assert cmd.user_id == "u-bench"
        return BenchmarkResult(
            summary=BenchmarkSummary(data={"rows": 2}),
            rows=[BenchmarkRow(entry_id=1, question="Q1", data={})],
            run_id="run-test",
        )

    app.dependency_overrides[get_run_gold_qa_dataset_evaluation_use_case] = lambda: _CallableUseCase(_bench)

    r = tc.post(
        "/evaluation/dataset/run",
        headers=_uid_header("u-bench"),
        json={
            "project_id": "demo",
            "enable_query_rewrite": True,
            "enable_hybrid_retrieval": False,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["run_id"] == "run-test"
    assert data["summary"]["rows"] == 2
    assert len(data["rows"]) == 1


def test_evaluation_dataset_run_vector_store_503(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    def _raise(*a: Any, **k: Any) -> BenchmarkResult:
        raise VectorStoreError("v", user_message="store")

    app.dependency_overrides[get_run_gold_qa_dataset_evaluation_use_case] = lambda: _CallableUseCase(_raise)
    r = tc.post(
        "/evaluation/dataset/run",
        headers=_uid_header(),
        json={
            "project_id": "demo",
            "enable_query_rewrite": True,
            "enable_hybrid_retrieval": True,
        },
    )
    assert r.status_code == 503


def test_evaluation_export_benchmark_smoke(override_app: tuple[TestClient, FastAPI]) -> None:
    """End-to-end export route with the real export use case (pure application code)."""
    tc, app = override_app
    app.dependency_overrides[get_build_benchmark_export_artifacts_use_case] = (
        lambda: BuildBenchmarkExportArtifactsUseCase()
    )

    info = tc.get("/evaluation/export/benchmark")
    assert info.status_code == 200
    assert info.json().get("implemented") is True

    body = {
        "project_id": "demo",
        "enable_query_rewrite": False,
        "enable_hybrid_retrieval": True,
        "result": {"summary": {"rows": 0}, "rows": []},
    }
    r = tc.post("/evaluation/export/benchmark", json=body)
    assert r.status_code == 200
    bundle = r.json()
    raw = base64.standard_b64decode(bundle["json_base64"])
    assert json.loads(raw.decode("utf-8"))["metadata"]["project_id"] == "demo"


def test_value_error_not_found_maps_to_404(override_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = override_app

    def _missing(_uid: str, _pid: str) -> Project:
        raise ValueError("Project not found for user")

    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        _FakeProjectService(get_project_hook=_missing)
    )
    app.dependency_overrides[get_ask_question_use_case] = lambda: _CallableUseCase(lambda *a, **k: None)

    r = tc.post(
        "/chat/ask",
        headers=_uid_header(),
        json={"project_id": "ghost", "question": "Q"},
    )
    assert r.status_code == 404
    assert r.json().get("code") == "resource_not_found"
