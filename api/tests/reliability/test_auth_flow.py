"""Auth flows: register/login then authenticated ``/users/me`` (TestClient + overrides)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.auth.password_utils import hash_password
from interfaces.http.dependencies import get_user_repository
from interfaces.http.main import create_app


def _row(
    *,
    user_id: str = "u-auth-flow",
    username: str = "alice",
    password_plain: str = "secret123",
) -> dict[str, Any]:
    return {
        "id": 1,
        "username": username,
        "user_id": user_id,
        "password_hash": hash_password(password_plain),
        "display_name": "Alice",
        "avatar_path": None,
        "created_at": "2020-01-01T00:00:00",
    }


class _FakeRepo:
    def __init__(self, users_by_username: dict[str, dict[str, Any]]) -> None:
        self._by_username = {k.lower(): dict(v) for k, v in users_by_username.items()}

    def get_by_username(self, username: str):
        return self._by_username.get(username.strip().lower())

    def get_by_user_id(self, user_id: str):
        for u in self._by_username.values():
            if u["user_id"] == user_id:
                return dict(u)
        return None

    def username_exists(self, username: str) -> bool:
        return username.strip().lower() in self._by_username

    def create_user(self, username: str, password_hash: str, display_name: str):
        uid = "registered-reliability-uid"
        self._by_username[username.lower()] = {
            "id": 99,
            "username": username,
            "user_id": uid,
            "password_hash": password_hash,
            "display_name": display_name,
            "avatar_path": None,
            "created_at": "2021-01-01T00:00:00",
        }
        return {
            "username": username,
            "user_id": uid,
            "display_name": display_name,
            "avatar_path": None,
        }


def _auth_client_with_repo(repo: _FakeRepo) -> Any:
    app = create_app()
    app.dependency_overrides[get_user_repository] = lambda: repo
    return app


@pytest.mark.reliability
def test_register_then_users_me_flow() -> None:
    repo = _FakeRepo({})
    app = _auth_client_with_repo(repo)
    with TestClient(app) as tc:
        reg = tc.post(
            "/auth/register",
            json={
                "username": "reluser",
                "password": "pw12345678",
                "confirm_password": "pw12345678",
                "display_name": "Rel User",
            },
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        me = tc.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["username"] == "reluser"
        assert me.json()["user_id"] == "registered-reliability-uid"
    app.dependency_overrides.clear()


@pytest.mark.reliability
def test_login_then_users_me_flow() -> None:
    repo = _FakeRepo({"alice": _row()})
    app = _auth_client_with_repo(repo)
    with TestClient(app) as tc:
        login = tc.post("/auth/login", json={"username": "alice", "password": "secret123"})
        assert login.status_code == 200
        token = login.json()["access_token"]
        me = tc.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["user_id"] == "u-auth-flow"
    app.dependency_overrides.clear()
