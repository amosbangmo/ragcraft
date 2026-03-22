"""
Streamlit-facing auth entrypoints (login/register/session reads).

Pages and ``src/ui`` must import from here — not :mod:`src.auth.auth_service` — so the app can use
either local SQLite (in-process) or the FastAPI ``/auth/*`` routes when ``RAGCRAFT_BACKEND_CLIENT=http``.
"""

from __future__ import annotations

from src.auth.auth_service import AuthService
from src.frontend_gateway.errors import BackendHttpError
from src.frontend_gateway.http_transport import HttpTransport
from src.frontend_gateway.settings import load_frontend_backend_settings, use_http_backend_client
from src.frontend_gateway.streamlit_session import apply_auth_user_dict_to_streamlit_session


def _message_from_backend_error(exc: BackendHttpError) -> str:
    p = exc.payload
    if isinstance(p, dict):
        for key in ("message", "detail"):
            v = p.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return str(exc) or "Request failed."


def _http_transport() -> HttpTransport:
    s = load_frontend_backend_settings()
    return HttpTransport(
        base_url=s.api_base_url,
        connect_timeout=s.api_connect_timeout_seconds,
        read_timeout=s.api_read_timeout_seconds,
    )


def login(username: str, password: str) -> tuple[bool, str]:
    if not use_http_backend_client():
        return AuthService().login(username, password)
    transport = _http_transport()
    try:
        data = transport.request_json(
            "POST",
            "/auth/login",
            json_body={"username": username, "password": password},
            send_user_header=False,
        )
    except BackendHttpError as exc:
        return False, _message_from_backend_error(exc)
    finally:
        transport.close()
    if not isinstance(data, dict) or not data.get("success"):
        return False, str((data or {}).get("message") or "Login failed.")
    user = data.get("user")
    if not isinstance(user, dict):
        return False, "Invalid response from server."
    apply_auth_user_dict_to_streamlit_session(user)
    return True, str(data.get("message") or "Login successful.")


def register(
    *,
    username: str,
    password: str,
    confirm_password: str,
    display_name: str,
) -> tuple[bool, str]:
    if not use_http_backend_client():
        return AuthService().register(
            username=username,
            password=password,
            confirm_password=confirm_password,
            display_name=display_name,
        )
    transport = _http_transport()
    try:
        data = transport.request_json(
            "POST",
            "/auth/register",
            json_body={
                "username": username,
                "password": password,
                "confirm_password": confirm_password,
                "display_name": display_name,
            },
            send_user_header=False,
        )
    except BackendHttpError as exc:
        return False, _message_from_backend_error(exc)
    finally:
        transport.close()
    if not isinstance(data, dict) or not data.get("success"):
        return False, str((data or {}).get("message") or "Registration failed.")
    user = data.get("user")
    if not isinstance(user, dict):
        return False, "Invalid response from server."
    apply_auth_user_dict_to_streamlit_session(user)
    return True, str(data.get("message") or "Account created successfully.")


def logout() -> None:
    AuthService().logout()


def is_authenticated() -> bool:
    return AuthService().is_authenticated()


def get_display_name() -> str | None:
    return AuthService().get_display_name()


def get_current_avatar_path() -> str | None:
    return AuthService().get_current_avatar_path()


def get_current_user_id() -> str | None:
    return AuthService().get_current_user_id()
