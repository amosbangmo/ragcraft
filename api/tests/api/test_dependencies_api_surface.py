from __future__ import annotations

import sys

import pytest

import interfaces.http.dependencies as api_dependencies

# Historical monolith Streamlit entry module name; loading the API graph must not import it.
_LEGACY_MONOLITH_STREAMLIT_APP = "src.app.ragcraft_app"


def test_legacy_app_shell_not_exposed_from_dependencies() -> None:
    """FastAPI wiring uses the application container only; the Streamlit façade is not a DI export."""
    assert not hasattr(api_dependencies, "get_ragcraft_app")


def test_primary_container_getter_is_cached() -> None:
    assert callable(api_dependencies.get_backend_application_container)
    assert (
        getattr(api_dependencies.get_backend_application_container, "cache_info", None) is not None
    )


def test_dependencies_module_has_no_legacy_db_bootstrap() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3]
        / "api"
        / "src"
        / "interfaces"
        / "http"
        / "dependencies.py"
    ).read_text(encoding="utf-8")
    assert "ensure_auth_database" not in source
    assert "get_user_repository" in source
    assert "BackendContainerDep" in source


def test_dependencies_avoids_legacy_streamlit_facade_imports() -> None:
    """Guards the FastAPI graph against the Streamlit façade (see interfaces.http.dependencies)."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3]
        / "api"
        / "src"
        / "interfaces"
        / "http"
        / "dependencies.py"
    ).read_text(encoding="utf-8")
    assert "ragcraft_app" not in source
    assert "RAGCraftApp" not in source


def test_backend_container_resolution_avoids_legacy_app_module() -> None:
    """Instantiating the API composition root must not load the removed monolith UI module."""
    sys.modules.pop(_LEGACY_MONOLITH_STREAMLIT_APP, None)

    api_dependencies.get_backend_application_container.cache_clear()

    try:
        container = api_dependencies.get_backend_application_container()
    except Exception as exc:  # pragma: no cover - env-specific (DB, optional deps)
        pytest.skip(f"Backend container unavailable in this environment: {exc}")

    assert _LEGACY_MONOLITH_STREAMLIT_APP not in sys.modules
    assert container.project_service is not None
    assert container.chat_ask_question_use_case is not None
    assert container.evaluation_list_retrieval_query_logs_use_case is not None
    assert container.evaluation_build_benchmark_export_artifacts_use_case is not None
