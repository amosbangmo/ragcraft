"""
Streamlit session singletons for resolving a :class:`~src.frontend_gateway.protocol.BackendClient`.

Pages and ``src/ui`` must call :func:`get_backend_client` (via
:mod:`src.frontend_gateway.streamlit_api_client` / :mod:`src.frontend_gateway.streamlit_context`).
**Default:** :class:`~src.frontend_gateway.http_client.HttpBackendClient` (``RAGCRAFT_BACKEND_CLIENT`` unset
or ``http``). **Escape hatch:** ``RAGCRAFT_BACKEND_CLIENT=in_process`` caches a
:class:`~src.composition.BackendApplicationContainer` from
:func:`~src.frontend_gateway.streamlit_backend_factory.build_streamlit_backend_application_container`.
"""

from __future__ import annotations

import streamlit as st

from src.composition import BackendApplicationContainer
from src.frontend_gateway.protocol import BackendClient
from src.frontend_gateway.settings import load_frontend_backend_settings, use_http_backend_client


BACKEND_CONTAINER_KEY = "streamlit_backend_application_container"
HTTP_BACKEND_CLIENT_KEY = "ragcraft_http_backend_client"


def _get_streamlit_backend_container() -> BackendApplicationContainer:
    if BACKEND_CONTAINER_KEY not in st.session_state:
        from src.frontend_gateway.streamlit_backend_factory import (
            build_streamlit_backend_application_container,
        )

        st.session_state[BACKEND_CONTAINER_KEY] = build_streamlit_backend_application_container()

    return st.session_state[BACKEND_CONTAINER_KEY]


def get_backend_client() -> BackendClient:
    """Return :class:`~src.frontend_gateway.in_process.InProcessBackendClient` or :class:`~src.frontend_gateway.http_client.HttpBackendClient`."""
    if use_http_backend_client():
        from src.frontend_gateway.http_client import HttpBackendClient

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

    from src.frontend_gateway.in_process import InProcessBackendClient

    return InProcessBackendClient(_get_streamlit_backend_container())


def reset_app():
    """
    Reset the application singleton.
    Useful for debugging or resetting state.
    """

    if BACKEND_CONTAINER_KEY in st.session_state:
        del st.session_state[BACKEND_CONTAINER_KEY]
    st.session_state.pop(HTTP_BACKEND_CLIENT_KEY, None)
