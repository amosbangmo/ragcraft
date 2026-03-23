from __future__ import annotations

from unittest.mock import MagicMock, patch

from services.streamlit_context import refresh_streamlit_auth_session_from_user_id


def test_refresh_streamlit_auth_session_from_user_id_delegates_to_auth_service() -> None:
    mock_service = MagicMock()
    with patch("services.settings.use_http_backend_client", return_value=False):
        with patch("infrastructure.auth.auth_service.AuthService", return_value=mock_service):
            refresh_streamlit_auth_session_from_user_id("user-42")
    mock_service.refresh_session_from_user_id.assert_called_once_with("user-42")


def test_refresh_streamlit_auth_session_pulls_http_profile_when_api_mode() -> None:
    mock_client = MagicMock()
    mock_client.get_current_user_record.return_value = {
        "username": "alice",
        "user_id": "u1",
        "display_name": "Alice",
        "avatar_path": None,
        "created_at": None,
    }
    with patch("services.settings.use_http_backend_client", return_value=True):
        with patch(
            "services.streamlit_context.get_backend_client",
            return_value=mock_client,
        ):
            with patch(
                "services.streamlit_session.apply_auth_user_dict_to_streamlit_session"
            ) as apply:
                refresh_streamlit_auth_session_from_user_id("u1")
                apply.assert_called_once_with(
                    mock_client.get_current_user_record.return_value
                )
