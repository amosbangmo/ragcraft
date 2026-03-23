"""
Write Streamlit session auth fields after HTTP profile/login responses.

Uses the same ``session_state`` keys as :class:`~infrastructure.auth.auth_service.AuthService` so
``get_user_id()`` and navigation stay consistent.
"""

from __future__ import annotations

from typing import Any


def apply_auth_user_dict_to_streamlit_session(
    user: dict[str, Any],
    *,
    access_token: str | None = None,
) -> None:
    """Populate Streamlit session from a user profile dict (API or SQLite row-shaped)."""
    import streamlit as st

    from infrastructure.auth.auth_service import AuthService

    st.session_state[AuthService.SESSION_AUTH_KEY] = True
    st.session_state[AuthService.SESSION_USER_KEY] = str(user["username"])
    st.session_state[AuthService.SESSION_USER_ID_KEY] = str(user["user_id"])
    st.session_state[AuthService.SESSION_DISPLAY_NAME_KEY] = str(user["display_name"])
    st.session_state[AuthService.SESSION_AVATAR_KEY] = user.get("avatar_path")
    tok = (access_token or "").strip() or (str(user.get("access_token") or "").strip())
    if tok:
        st.session_state[AuthService.SESSION_ACCESS_TOKEN_KEY] = tok
    else:
        st.session_state.pop(AuthService.SESSION_ACCESS_TOKEN_KEY, None)
