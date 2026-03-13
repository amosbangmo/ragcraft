import streamlit as st

from src.auth.auth_service import AuthService


def require_authentication(current_page: str):
    """
    Block access to protected pages when the user is not authenticated.
    Store the requested page for redirection after login.
    """
    auth_service = AuthService()

    if auth_service.is_authenticated():
        return

    st.session_state["post_login_redirect"] = current_page
    st.warning("Please log in to access this page.")
    st.switch_page("pages/login.py")
