"""Resolve the HTTP backend client for the current Streamlit session."""

from __future__ import annotations

from services.backend_client_protocol import BackendClient
from services.settings import FrontendBackendSettings, load_frontend_backend_settings


def get_backend_client() -> BackendClient:
    from infrastructure.config.app_state import get_backend_client as _core

    return _core()


def get_frontend_backend_settings() -> FrontendBackendSettings:
    return load_frontend_backend_settings()
