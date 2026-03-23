"""Transport dependency resolves :class:`~domain.authenticated_principal.AuthenticatedPrincipal` via JWT."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from interfaces.http.dependencies import get_authenticated_principal, get_authentication_port
from interfaces.http.error_handlers import register_exception_handlers
from domain.auth.authenticated_principal import AuthenticatedPrincipal
from infrastructure.auth.jwt_auth_settings import JwtAuthSettings
from infrastructure.auth.jwt_authentication_adapter import JwtAuthenticationAdapter
from apps_api.bearer_auth import bearer_headers


def _jwt_adapter() -> JwtAuthenticationAdapter:
    return JwtAuthenticationAdapter(JwtAuthSettings.from_env())


def test_get_authenticated_principal_missing_authorization_401() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.dependency_overrides[get_authentication_port] = lambda: _jwt_adapter()

    @app.get("/who")
    def who(p: AuthenticatedPrincipal = Depends(get_authenticated_principal)) -> dict[str, str]:
        return {"user_id": p.user_id}

    with TestClient(app) as tc:
        r = tc.get("/who")
    assert r.status_code == 401
    body = r.json()
    assert body.get("code") == "authentication_required"


def test_get_authenticated_principal_valid_bearer() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.dependency_overrides[get_authentication_port] = lambda: _jwt_adapter()

    @app.get("/who")
    def who(p: AuthenticatedPrincipal = Depends(get_authenticated_principal)) -> dict[str, str]:
        return {"user_id": p.user_id}

    with TestClient(app) as tc:
        r = tc.get("/who", headers=bearer_headers(user_id="  uid-42  "))
    assert r.status_code == 200
    assert r.json() == {"user_id": "uid-42"}


def test_get_authenticated_principal_invalid_token_401() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.dependency_overrides[get_authentication_port] = lambda: _jwt_adapter()

    @app.get("/who")
    def who(p: AuthenticatedPrincipal = Depends(get_authenticated_principal)) -> dict[str, str]:
        return {"user_id": p.user_id}

    with TestClient(app) as tc:
        r = tc.get("/who", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401
    assert r.json().get("code") == "invalid_token"


def test_get_authenticated_principal_malformed_scheme_400() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.dependency_overrides[get_authentication_port] = lambda: _jwt_adapter()

    @app.get("/who")
    def who(p: AuthenticatedPrincipal = Depends(get_authenticated_principal)) -> dict[str, str]:
        return {"user_id": p.user_id}

    with TestClient(app) as tc:
        r = tc.get("/who", headers={"Authorization": "Basic abc"})
    assert r.status_code == 400
    assert r.json().get("code") == "malformed_authorization_header"


@pytest.mark.parametrize(
    "header_value",
    ["Bearer", "Bearer ", ""],
)
def test_get_authenticated_principal_empty_bearer_token_400(header_value: str) -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.dependency_overrides[get_authentication_port] = lambda: _jwt_adapter()

    @app.get("/who")
    def who(p: AuthenticatedPrincipal = Depends(get_authenticated_principal)) -> dict[str, str]:
        return {"user_id": p.user_id}

    with TestClient(app) as tc:
        r = tc.get("/who", headers={"Authorization": header_value} if header_value else {})
    if not header_value:
        assert r.status_code == 401
        assert r.json().get("code") == "authentication_required"
    else:
        assert r.status_code == 400
        assert r.json().get("code") == "malformed_authorization_header"
