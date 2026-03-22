from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.frontend_gateway import streamlit_auth


def test_login_delegates_to_auth_service_when_in_process() -> None:
    mock_svc = MagicMock()
    mock_svc.login.return_value = (True, "ok")
    with patch("src.frontend_gateway.streamlit_auth.use_http_backend_client", return_value=False):
        with patch("src.frontend_gateway.streamlit_auth.AuthService", return_value=mock_svc):
            ok, msg = streamlit_auth.login("u", "p")
    assert ok and msg == "ok"
    mock_svc.login.assert_called_once_with("u", "p")


def test_logout_delegates_to_auth_service() -> None:
    mock_svc = MagicMock()
    with patch("src.frontend_gateway.streamlit_auth.AuthService", return_value=mock_svc):
        streamlit_auth.logout()
    mock_svc.logout.assert_called_once()
