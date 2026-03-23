"""Transport dependency builds :class:`~src.application.auth.authenticated_principal.AuthenticatedPrincipal`."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from apps.api.dependencies import get_authenticated_principal
from src.application.auth.authenticated_principal import AuthenticatedPrincipal


def test_get_authenticated_principal_missing_header_400() -> None:
    app = FastAPI()

    @app.get("/who")
    def who(p: AuthenticatedPrincipal = Depends(get_authenticated_principal)) -> dict[str, str]:
        return {"user_id": p.user_id}

    with TestClient(app) as tc:
        r = tc.get("/who")
    assert r.status_code == 400


def test_get_authenticated_principal_populated() -> None:
    app = FastAPI()

    @app.get("/who")
    def who(p: AuthenticatedPrincipal = Depends(get_authenticated_principal)) -> dict[str, str]:
        return {"user_id": p.user_id, "method": p.auth_method}

    with TestClient(app) as tc:
        r = tc.get("/who", headers={"X-User-Id": "  uid-42  "})
    assert r.status_code == 200
    assert r.json() == {"user_id": "uid-42", "method": "x_user_id_header"}
