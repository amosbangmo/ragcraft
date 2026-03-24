from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

import services.session.streamlit_auth as streamlit_auth
from infrastructure.auth.auth_service import AuthService


def test_login_uses_http_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_transport = MagicMock()
    mock_transport.request_json.return_value = {
        "success": True,
        "message": "ok",
        "user": {"username": "u", "user_id": "1", "display_name": "U"},
        "access_token": "tok",
    }
    mock_transport.close = MagicMock()
    with patch.object(streamlit_auth, "_http_transport", return_value=mock_transport):
        with patch("services.session.streamlit_session.apply_auth_user_dict_to_streamlit_session"):
            ok, msg = streamlit_auth.login("u", "p")
    assert ok and msg == "ok"
    mock_transport.request_json.assert_called_once()
    mock_transport.close.assert_called_once()


def test_logout_clears_session_without_auth_service_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state: dict = {
        AuthService.SESSION_AUTH_KEY: True,
        AuthService.SESSION_USER_KEY: "alice",
        AuthService.SESSION_USER_ID_KEY: "uid-1",
        AuthService.SESSION_DISPLAY_NAME_KEY: "Alice",
        AuthService.SESSION_AVATAR_KEY: "/a.png",
        AuthService.SESSION_ACCESS_TOKEN_KEY: "tok",
        "project_id": "p1",
    }
    fake_st = types.ModuleType("streamlit")
    fake_st.session_state = state
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)

    streamlit_auth.logout()

    assert state.get(AuthService.SESSION_AUTH_KEY) is False
    assert AuthService.SESSION_USER_KEY not in state
    assert AuthService.SESSION_USER_ID_KEY not in state
    assert AuthService.SESSION_ACCESS_TOKEN_KEY not in state
    assert "project_id" not in state
