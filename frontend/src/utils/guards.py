import streamlit as st

from services import streamlit_auth


def require_authentication(current_page: str) -> None:
    """
    Block access to protected pages when the user is not authenticated.
    Store the requested page for redirection after login.
    """
    if streamlit_auth.is_authenticated():
        return

    st.session_state["post_login_redirect"] = current_page
    st.warning("Please log in to access this page.")
    st.switch_page("pages/login.py")
