"""
Streamlit ↔ backend resolution (HTTP vs in-process).

Used by :mod:`services.api_client` so feature code does not import infrastructure or composition
roots directly.
"""

from __future__ import annotations

from application.frontend_support.backend_client_protocol import BackendClient
from services.settings import (
    FrontendBackendSettings,
    load_frontend_backend_settings,
    use_http_backend_client,
)


def get_backend_client() -> BackendClient:
    from infrastructure.config.app_state import get_backend_client as _core

    return _core()


def get_frontend_backend_settings() -> FrontendBackendSettings:
    return load_frontend_backend_settings()


def is_http_backend_mode() -> bool:
    return use_http_backend_client()
