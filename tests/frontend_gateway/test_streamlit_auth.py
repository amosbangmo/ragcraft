from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

import src.frontend_gateway.streamlit_auth as streamlit_auth
from src.auth.auth_service import AuthService


def test_login_delegates_to_auth_service_when_in_process() -> None:
    mock_svc = MagicMock()
    mock_svc.login.return_value = (True, "ok")
    with patch.object(streamlit_auth, "use_http_backend_client", return_value=False):
        with patch.object(streamlit_auth, "AuthService", return_value=mock_svc):
            ok, msg = streamlit_auth.login("u", "p")
    assert ok and msg == "ok"
    mock_svc.login.assert_called_once_with("u", "p")


def test_logout_clears_session_without_auth_service_instance(monkeypatch: pytest.MonkeyPatch) -> None:
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
