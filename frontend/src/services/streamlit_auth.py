"""
Streamlit-facing auth entrypoints (login/register/session reads).

Uses FastAPI ``/auth/login`` and ``/auth/register`` plus Streamlit ``session_state`` keys.

Multipage navigations can perform a full browser load; ``session_state`` may not carry over until
the WebSocket reconnects. A short-lived first-party cookie mirrors the bearer token so
``require_authentication`` can rehydrate via ``GET /users/me`` on the next document request.
"""

from __future__ import annotations

import json

import streamlit.components.v1 as components

from infrastructure.auth.auth_service import AuthService
from services.errors import BackendHttpError
from services.http_transport import HttpTransport
from services.settings import load_frontend_backend_settings
from services.streamlit_session import apply_auth_user_dict_to_streamlit_session

# Browser cookie (not HttpOnly) so the embedded components iframe can set it on the app origin.
_STREAMLIT_ACCESS_COOKIE = "ragcraft_streamlit_access"
_COOKIE_MAX_AGE_S = 86400 * 7


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


def _emit_access_token_cookie(access_token: str) -> None:
    tok = str(access_token or "").strip()
    if not tok:
        return
    payload = json.dumps(tok)
    cname = _STREAMLIT_ACCESS_COOKIE
    max_age = _COOKIE_MAX_AGE_S
    components.html(
        f"""
        <script>
        (function () {{
          const v = {payload};
          const c =
            "{cname}=" +
            encodeURIComponent(v) +
            "; path=/; SameSite=Lax; max-age={max_age}";
          try {{
            window.parent.document.cookie = c;
          }} catch (e) {{
            document.cookie = c;
          }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def _clear_access_token_cookie() -> None:
    cname = _STREAMLIT_ACCESS_COOKIE
    components.html(
        f"""
        <script>
        (function () {{
          const c = "{cname}=; path=/; SameSite=Lax; max-age=0";
          try {{
            window.parent.document.cookie = c;
          }} catch (e) {{
            document.cookie = c;
          }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def try_restore_session_from_browser_cookie() -> bool:
    """Repopulate ``session_state`` from the mirrored JWT cookie after a multipage document load."""
    import streamlit as st

    if is_authenticated():
        return True
    try:
        raw = st.context.cookies.to_dict().get(_STREAMLIT_ACCESS_COOKIE)
    except (AttributeError, RuntimeError, TypeError):
        return False
    if raw is None:
        return False
    token = str(raw).strip()
    if not token:
        return False
    transport = _http_transport()
    try:
        data = transport.request_json(
            "GET",
            "/users/me",
            bearer_token=token,
            send_authorization=True,
        )
    except BackendHttpError:
        return False
    finally:
        transport.close()
    if not isinstance(data, dict):
        return False
    user = {
        "username": data["username"],
        "user_id": data["user_id"],
        "display_name": data["display_name"],
        "avatar_path": data.get("avatar_path"),
    }
    apply_auth_user_dict_to_streamlit_session(user, access_token=token)
    return True


def login(username: str, password: str) -> tuple[bool, str]:
    transport = _http_transport()
    try:
        data = transport.request_json(
            "POST",
            "/auth/login",
            json_body={"username": username, "password": password},
            send_authorization=False,
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
    tok = str(data.get("access_token") or "").strip() or None
    apply_auth_user_dict_to_streamlit_session(user, access_token=tok)
    _emit_access_token_cookie(tok or "")
    return True, str(data.get("message") or "Login successful.")


def register(
    *,
    username: str,
    password: str,
    confirm_password: str,
    display_name: str,
) -> tuple[bool, str]:
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
            send_authorization=False,
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
    tok = str(data.get("access_token") or "").strip() or None
    apply_auth_user_dict_to_streamlit_session(user, access_token=tok)
    _emit_access_token_cookie(tok or "")
    return True, str(data.get("message") or "Account created successfully.")


def logout() -> None:
    import streamlit as st

    st.session_state[AuthService.SESSION_AUTH_KEY] = False
    st.session_state.pop(AuthService.SESSION_USER_KEY, None)
    st.session_state.pop(AuthService.SESSION_USER_ID_KEY, None)
    st.session_state.pop(AuthService.SESSION_DISPLAY_NAME_KEY, None)
    st.session_state.pop(AuthService.SESSION_AVATAR_KEY, None)
    st.session_state.pop(AuthService.SESSION_ACCESS_TOKEN_KEY, None)
    st.session_state.pop("project_id", None)
    _clear_access_token_cookie()


def is_authenticated() -> bool:
    import streamlit as st

    return bool(st.session_state.get(AuthService.SESSION_AUTH_KEY, False))


def get_display_name() -> str | None:
    import streamlit as st

    v = st.session_state.get(AuthService.SESSION_DISPLAY_NAME_KEY)
    return str(v) if v is not None else None


def get_current_avatar_path() -> str | None:
    import streamlit as st

    return st.session_state.get(AuthService.SESSION_AVATAR_KEY)


def get_current_user_id() -> str | None:
    import streamlit as st

    v = st.session_state.get(AuthService.SESSION_USER_ID_KEY)
    return str(v) if v is not None else None
