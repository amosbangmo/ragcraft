from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.frontend_gateway.streamlit_context import refresh_streamlit_auth_session_from_user_id


def test_refresh_streamlit_auth_session_from_user_id_delegates_to_auth_service() -> None:
    mock_service = MagicMock()
    with patch("src.auth.auth_service.AuthService", return_value=mock_service):
        refresh_streamlit_auth_session_from_user_id("user-42")
    mock_service.refresh_session_from_user_id.assert_called_once_with("user-42")
