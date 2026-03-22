"""
Frontend boundary: protocol, HTTP and in-process clients, Streamlit settings.

Exports are loaded lazily (PEP 562) so ``import src.frontend_gateway.<submodule>`` does not
eagerly import the in-process client or :class:`~src.app.ragcraft_app.RAGCraftApp`.
"""

from __future__ import annotations

__all__ = [
    "BackendClient",
    "HttpBackendClient",
    "InProcessBackendClient",
    "load_frontend_backend_settings",
    "use_http_backend_client",
]


def __getattr__(name: str):
    if name == "BackendClient":
        from src.frontend_gateway.protocol import BackendClient

        return BackendClient
    if name == "HttpBackendClient":
        from src.frontend_gateway.http_client import HttpBackendClient

        return HttpBackendClient
    if name == "InProcessBackendClient":
        from src.frontend_gateway.in_process import InProcessBackendClient

        return InProcessBackendClient
    if name in ("load_frontend_backend_settings", "use_http_backend_client"):
        from src.frontend_gateway import settings as _settings

        return getattr(_settings, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
