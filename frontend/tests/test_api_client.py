"""Guardrails for the canonical Streamlit ↔ backend import surface."""

from __future__ import annotations

import inspect

import pytest


def test_api_client_exports_backend_facade_symbols() -> None:
    import services.api_client as ac

    for name in (
        "BackendClient",
        "HttpBackendClient",
        "get_backend_client",
        "get_frontend_backend_settings",
        "is_http_backend_mode",
    ):
        assert hasattr(ac, name), f"missing api_client export: {name}"
        assert name in ac.__all__


def test_in_process_client_is_lazy_export() -> None:
    """Importing api_client must not load the in-process implementation (see lazy-import test)."""
    import services.api_client as ac

    assert "InProcessBackendClient" in ac.__all__
    cls = ac.InProcessBackendClient
    assert inspect.isclass(cls)


@pytest.mark.parametrize(
    "name",
    [
        "BenchmarkResult",
        "RetrievalSettings",
        "default_retrieval_preset_merge_port",
    ],
)
def test_api_client_exports_ui_integration_helpers(name: str) -> None:
    import services.api_client as ac

    assert name in ac.__all__
    assert hasattr(ac, name)
