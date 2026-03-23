from __future__ import annotations

__all__ = [
    "BackendClient",
    "HttpBackendClient",
    "get_backend_client",
    "get_frontend_backend_settings",
    "load_frontend_backend_settings",
    "streamlit_auth",
]


def __getattr__(name: str):
    if name == "streamlit_auth":
        import importlib

        return importlib.import_module("services.streamlit_auth")
    if name in (
        "BackendClient",
        "HttpBackendClient",
    ):
        from services import api_client as _ac

        return getattr(_ac, name)
    if name == "load_frontend_backend_settings":
        from services import settings as _settings

        return getattr(_settings, name)
    if name in ("get_backend_client", "get_frontend_backend_settings"):
        from services import api_client as _ac

        return getattr(_ac, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
