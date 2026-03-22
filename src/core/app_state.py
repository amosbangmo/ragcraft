"""
Streamlit session singletons for the backend boundary.

Pages and ``src/ui`` must call :func:`get_backend_client` (via
:mod:`src.frontend_gateway.streamlit_api_client` / :mod:`src.frontend_gateway.streamlit_context`).
:class:`~src.app.ragcraft_app.RAGCraftApp` is only constructed here for the default in-process adapter.
"""

import streamlit as st
from src.app.ragcraft_app import RAGCraftApp
from src.frontend_gateway.protocol import BackendClient
from src.frontend_gateway.settings import load_frontend_backend_settings, use_http_backend_client


APP_KEY = "ragcraft_app"
HTTP_BACKEND_CLIENT_KEY = "ragcraft_http_backend_client"


def get_app() -> RAGCraftApp:
    """
    Singleton in-process façade used exclusively to build :class:`~src.frontend_gateway.in_process.InProcessBackendClient`.

    Feature code should not call this; use :func:`get_backend_client` instead.
    """

    if APP_KEY not in st.session_state:
        st.session_state[APP_KEY] = RAGCraftApp()

    return st.session_state[APP_KEY]


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

    return InProcessBackendClient(get_app())


def reset_app():
    """
    Reset the application singleton.
    Useful for debugging or resetting state.
    """

    if APP_KEY in st.session_state:
        del st.session_state[APP_KEY]
    st.session_state.pop(HTTP_BACKEND_CLIENT_KEY, None)
