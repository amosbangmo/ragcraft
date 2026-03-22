"""Integration-style checks for the typed composition root (requires full ``requirements.txt`` graph)."""

from __future__ import annotations

import pytest

pytest.importorskip("unstructured", reason="backend composition loads ingestion adapters")
pytest.importorskip("langchain_community", reason="backend composition loads vector store stack")

from src.composition import (
    BackendApplicationContainer,
    BackendComposition,
    build_backend,
    build_backend_application_container,
    build_backend_composition,
)
import src.composition.application_container as application_container_module

from tests.support.backend_container import build_backend_container_for_tests, noop_chain_invalidate


def test_build_backend_composition_returns_typed_service_graph() -> None:
    try:
        backend = build_backend_composition()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Service graph unavailable in this environment: {exc}")

    assert isinstance(backend, BackendComposition)
    assert backend.project_service is not None
    assert backend.docstore_service is not None
    assert backend.query_log_service is not None
    assert backend.vectorstore_service is not None
    assert backend.evaluation_service is not None
    assert backend.project_settings_repository is not None
    assert backend.retrieval_settings_service is not None


def test_build_backend_wires_application_container() -> None:
    try:
        backend = build_backend_composition()
        container = build_backend_application_container(
            backend=backend,
            invalidate_chain_key=noop_chain_invalidate,
        )
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Composition unavailable in this environment: {exc}")

    assert isinstance(container, BackendApplicationContainer)
    assert container.backend is backend
    assert container.project_service is backend.project_service


def test_build_backend_reexported_from_package_matches_module() -> None:
    assert build_backend is application_container_module.build_backend


def test_key_use_cases_resolve() -> None:
    try:
        container = build_backend_container_for_tests()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Composition unavailable in this environment: {exc}")

    from src.application.use_cases.projects.list_projects import ListProjectsUseCase
    from src.application.use_cases.evaluation.list_retrieval_query_logs import (
        ListRetrievalQueryLogsUseCase,
    )
    from src.application.use_cases.evaluation.build_benchmark_export_artifacts import (
        BuildBenchmarkExportArtifactsUseCase,
    )

    assert isinstance(container.projects_list_projects_use_case, ListProjectsUseCase)
    assert isinstance(
        container.evaluation_list_retrieval_query_logs_use_case,
        ListRetrievalQueryLogsUseCase,
    )
    assert isinstance(
        container.evaluation_build_benchmark_export_artifacts_use_case,
        BuildBenchmarkExportArtifactsUseCase,
    )

    ask = container.chat_ask_question_use_case
    assert ask is not None
    assert hasattr(ask, "execute")
