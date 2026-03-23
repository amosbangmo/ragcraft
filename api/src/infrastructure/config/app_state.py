"""
Streamlit session singleton for the HTTP :class:`~services.http_backend_client.HttpBackendClient`.

Pages obtain the client via :mod:`services.api_client` / :mod:`services.backend_session`.
"""

from __future__ import annotations

import streamlit as st

from services.backend_client_protocol import BackendClient
from services.settings import load_frontend_backend_settings

HTTP_BACKEND_CLIENT_KEY = "ragcraft_http_backend_client"


def get_backend_client() -> BackendClient:
    """Return the cached HTTP client for the current API base URL and timeouts."""
    from services.http_backend_client import HttpBackendClient

    cfg = load_frontend_backend_settings()
    cached = st.session_state.get(HTTP_BACKEND_CLIENT_KEY)
    if isinstance(cached, HttpBackendClient) and (
        cached.base_url == cfg.api_base_url
        and cached.connect_timeout == cfg.api_connect_timeout_seconds
        and cached.read_timeout == cfg.api_read_timeout_seconds
    ):
        return cached
    client = HttpBackendClient(
        base_url=cfg.api_base_url,
        connect_timeout=cfg.api_connect_timeout_seconds,
        read_timeout=cfg.api_read_timeout_seconds,
    )
    st.session_state[HTTP_BACKEND_CLIENT_KEY] = client
    return client


def reset_app() -> None:
    st.session_state.pop(HTTP_BACKEND_CLIENT_KEY, None)
