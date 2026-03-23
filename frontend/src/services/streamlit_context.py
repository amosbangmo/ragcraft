"""
Streamlit wiring for :class:`~services.protocol.BackendClient` and session user id.

Re-exports :func:`~services.streamlit_api_client.get_backend_client` alongside
:func:`get_user_id`. UI modules may import both from here; pages may use either this module or
:mod:`services.streamlit_api_client`.
"""

from __future__ import annotations

from services.streamlit_api_client import get_backend_client


def get_user_id() -> str:
    from infrastructure.config.session import get_user_id as _get_user_id

    return _get_user_id()


def refresh_streamlit_auth_session_from_user_id(user_id: str) -> None:
    """
    Reload Streamlit session auth fields after profile mutations via ``BackendClient``.

    In HTTP backend mode, pulls ``GET /users/me`` instead of reading SQLite in-process.
    """
    from services.settings import use_http_backend_client
    from services.streamlit_api_client import get_backend_client
    from services.streamlit_session import apply_auth_user_dict_to_streamlit_session

    if use_http_backend_client():
        record = get_backend_client().get_current_user_record()
        if isinstance(record, dict):
            apply_auth_user_dict_to_streamlit_session(record)
        return

    from infrastructure.auth.auth_service import AuthService

    AuthService().refresh_session_from_user_id(user_id)
