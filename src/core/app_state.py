import streamlit as st
from src.app.ragcraft_app import RAGCraftApp
from src.frontend_gateway.protocol import BackendClient


APP_KEY = "ragcraft_app"


def get_app() -> RAGCraftApp:
    """
    Return a singleton RAGCraftApp instance
    stored in Streamlit session_state.
    """

    if APP_KEY not in st.session_state:
        st.session_state[APP_KEY] = RAGCraftApp()

    return st.session_state[APP_KEY]


def get_backend_client() -> BackendClient:
    """Streamlit entrypoint for backend operations; swap implementation for HTTP later."""
    from src.frontend_gateway.in_process import InProcessBackendClient

    return InProcessBackendClient(get_app())


def reset_app():
    """
    Reset the application singleton.
    Useful for debugging or resetting state.
    """

    if APP_KEY in st.session_state:
        del st.session_state[APP_KEY]
