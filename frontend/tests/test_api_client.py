"""Guardrails for the canonical Streamlit ↔ backend import surface."""

from __future__ import annotations


def test_api_client_exports_backend_facade_symbols() -> None:
    import services.api_client as ac

    for name in (
        "BackendClient",
        "HttpBackendClient",
        "get_backend_client",
        "get_frontend_backend_settings",
    ):
        assert hasattr(ac, name), f"missing api_client export: {name}"
        assert name in ac.__all__


def test_api_client_exports_ui_integration_helpers() -> None:
    import services.api_client as ac

    for name in (
        "BenchmarkResult",
        "RetrievalSettingsPayload",
        "SummaryRecallPreviewPayload",
        "default_retrieval_preset_merge_port",
    ):
        assert name in ac.__all__
        assert hasattr(ac, name)
