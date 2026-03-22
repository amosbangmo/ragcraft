import streamlit as st
from src.app.ragcraft_app import RAGCraftApp
from src.frontend_gateway.protocol import BackendClient
from src.frontend_gateway.settings import load_frontend_backend_settings, use_http_backend_client


APP_KEY = "ragcraft_app"
HTTP_BACKEND_CLIENT_KEY = "ragcraft_http_backend_client"


def get_app() -> RAGCraftApp:
    """
    Return a singleton RAGCraftApp instance
    stored in Streamlit session_state.
    """

    if APP_KEY not in st.session_state:
        st.session_state[APP_KEY] = RAGCraftApp()

    return st.session_state[APP_KEY]


def get_backend_client() -> BackendClient:
    """Streamlit entrypoint: in-process façade (default) or HTTP API (``RAGCRAFT_BACKEND_CLIENT=http``)."""
    if use_http_backend_client():
        from src.frontend_gateway.http_client import HttpBackendClient

        cfg = load_frontend_backend_settings()
        cached = st.session_state.get(HTTP_BACKEND_CLIENT_KEY)
        if isinstance(cached, HttpBackendClient) and getattr(cached, "base_url", "") == cfg.api_base_url:
            return cached
        client = HttpBackendClient(base_url=cfg.api_base_url, timeout=cfg.timeout_seconds)
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
