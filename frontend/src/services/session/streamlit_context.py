"""
Streamlit wiring for :class:`~services.api_client.BackendClient` and session user id.

Re-exports :func:`~services.api_client.get_backend_client` alongside :func:`get_user_id`.
Prefer :mod:`services.api_client` for new code.
"""

from __future__ import annotations

from services.api_client import get_backend_client


def get_user_id() -> str:
    from infrastructure.config.session import get_user_id as _get_user_id

    return _get_user_id()


def refresh_streamlit_auth_session_from_user_id(_user_id: str) -> None:
    """
    Reload Streamlit session auth fields after profile mutations via ``BackendClient``.

    Pulls ``GET /users/me`` over HTTP.
    """
    from services.session.streamlit_session import apply_auth_user_dict_to_streamlit_session

    record = get_backend_client().get_current_user_record()
    if isinstance(record, dict):
        apply_auth_user_dict_to_streamlit_session(record)
