from __future__ import annotations

__all__ = [
    "BackendClient",
    "HttpBackendClient",
    "InProcessBackendClient",
    "get_backend_client",
    "get_frontend_backend_settings",
    "is_http_backend_mode",
    "load_frontend_backend_settings",
    "streamlit_auth",
    "use_http_backend_client",
]


def __getattr__(name: str):
    if name == "streamlit_auth":
        import importlib

        return importlib.import_module("services.streamlit_auth")
    if name in (
        "BackendClient",
        "HttpBackendClient",
        "InProcessBackendClient",
    ):
        from services import api_client as _ac

        return getattr(_ac, name)
    if name in ("load_frontend_backend_settings", "use_http_backend_client"):
        from services import settings as _settings

        return getattr(_settings, name)
    if name in ("get_backend_client", "get_frontend_backend_settings", "is_http_backend_mode"):
        from services import api_client as _ac

        return getattr(_ac, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
