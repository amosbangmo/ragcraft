from __future__ import annotations

import apps.api.dependencies as api_dependencies


def test_legacy_ragcraft_app_dependency_removed() -> None:
    """FastAPI wiring uses the application container only; the Streamlit façade is not a DI export."""
    assert not hasattr(api_dependencies, "get_ragcraft_app")


def test_primary_container_getter_is_cached() -> None:
    assert callable(api_dependencies.get_backend_application_container)
    assert getattr(api_dependencies.get_backend_application_container, "cache_info", None) is not None
