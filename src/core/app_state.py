import streamlit as st
from src.app.ragcraft_app import RAGCraftApp


APP_KEY = "ragcraft_app"


def get_app() -> RAGCraftApp:
    """
    Return a singleton RAGCraftApp instance
    stored in Streamlit session_state.
    """

    if APP_KEY not in st.session_state:
        st.session_state[APP_KEY] = RAGCraftApp()

    return st.session_state[APP_KEY]


def reset_app():
    """
    Reset the application singleton.
    Useful for debugging or resetting state.
    """

    if APP_KEY in st.session_state:
        del st.session_state[APP_KEY]
