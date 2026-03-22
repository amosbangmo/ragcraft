"""
Streamlit wiring for :class:`~src.frontend_gateway.protocol.BackendClient` and session user id.

Re-exports :func:`~src.frontend_gateway.streamlit_api_client.get_backend_client`. Prefer importing
from :mod:`src.frontend_gateway.streamlit_api_client` in new code for clearer intent.
"""

from __future__ import annotations

from src.frontend_gateway.streamlit_api_client import get_backend_client


def get_user_id() -> str:
    from src.core.session import get_user_id as _get_user_id

    return _get_user_id()


def refresh_streamlit_auth_session_from_user_id(user_id: str) -> None:
    """Reload Streamlit session auth fields after profile mutations via ``BackendClient``."""
    from src.auth.auth_service import AuthService

    AuthService().refresh_session_from_user_id(user_id)
