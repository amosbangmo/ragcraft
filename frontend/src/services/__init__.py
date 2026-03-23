"""
Frontend boundary: protocol, HTTP and in-process clients, Streamlit settings.

Exports are loaded lazily (PEP 562) so ``import services.<submodule>`` does not
eagerly import HTTP or in-process backend clients unless those symbols are requested. The default
Streamlit mode is API-first (``RAGCRAFT_BACKEND_CLIENT=http``).
"""

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
    if name == "BackendClient":
        from services.protocol import BackendClient

        return BackendClient
    if name == "HttpBackendClient":
        from services.http_client import HttpBackendClient

        return HttpBackendClient
    if name == "InProcessBackendClient":
        from services.in_process import InProcessBackendClient

        return InProcessBackendClient
    if name in ("load_frontend_backend_settings", "use_http_backend_client"):
        from services import settings as _settings

        return getattr(_settings, name)
    if name in ("get_backend_client", "get_frontend_backend_settings", "is_http_backend_mode"):
        from services import streamlit_api_client as _sac

        return getattr(_sac, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
