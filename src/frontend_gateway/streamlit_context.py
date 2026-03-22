"""
Streamlit wiring for :class:`~src.frontend_gateway.protocol.BackendClient` and session user id.

UI modules import from here instead of ``src.core.app_state`` / ``src.core.session`` so
``src/ui`` does not depend on the composition-root module path (the implementation still
lives under ``src.core`` for the Streamlit host app).
"""

from __future__ import annotations

from src.frontend_gateway.protocol import BackendClient


def get_backend_client() -> BackendClient:
    from src.core.app_state import get_backend_client as _get_backend_client

    return _get_backend_client()


def get_user_id() -> str:
    from src.core.session import get_user_id as _get_user_id

    return _get_user_id()


def refresh_streamlit_auth_session_from_user_id(user_id: str) -> None:
    """Reload Streamlit session auth fields after profile mutations via ``BackendClient``."""
    from src.auth.auth_service import AuthService

    AuthService().refresh_session_from_user_id(user_id)
