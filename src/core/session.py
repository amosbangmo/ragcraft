import uuid
import streamlit as st


def get_user_id() -> str:
    """
    Return the authenticated user_id if present.
    Otherwise fall back to a temporary anonymous session id.
    """
    if "user_id" in st.session_state and st.session_state["user_id"]:
        return st.session_state["user_id"]

    if "anonymous_user_id" not in st.session_state:
        st.session_state["anonymous_user_id"] = str(uuid.uuid4())

    return st.session_state["anonymous_user_id"]
