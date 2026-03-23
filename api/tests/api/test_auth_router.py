"""Tests for ``/auth/login`` and ``/auth/register``."""

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
    user_id: str = "u1",
    username: str = "alice",
    display_name: str = "Alice",
    password_plain: str = "secret123",
) -> dict[str, Any]:
    return {
        "id": 1,
        "username": username,
        "user_id": user_id,
        "password_hash": hash_password(password_plain),
        "display_name": display_name,
        "avatar_path": None,
        "created_at": "2020-01-01T00:00:00",
    }


class FakeRepo:
    def __init__(self, users_by_username: dict[str, dict[str, Any]]):
        self._by_username = {k.lower(): dict(v) for k, v in users_by_username.items()}
        self.created: list[dict[str, Any]] = []

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
        uid = "newuid"
        self._by_username[username.lower()] = {
            "id": 99,
            "username": username,
            "user_id": uid,
            "password_hash": password_hash,
            "display_name": display_name,
            "avatar_path": None,
            "created_at": "2021-01-01T00:00:00",
        }
        self.created.append({"username": username, "display_name": display_name})
        return {
            "username": username,
            "user_id": uid,
            "display_name": display_name,
            "avatar_path": None,
        }


@pytest.fixture
def auth_app() -> tuple[TestClient, FastAPI]:
    app = create_app()
    with TestClient(app) as tc:
        yield tc, app
    app.dependency_overrides.clear()


def test_login_success(auth_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = auth_app
    alice = _row()
    app.dependency_overrides[get_user_repository] = lambda: FakeRepo({"alice": alice})
    r = tc.post("/auth/login", json={"username": "alice", "password": "secret123"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["token_type"] == "bearer"
    assert isinstance(body.get("access_token"), str) and len(body["access_token"]) > 20
    assert body["user"]["user_id"] == "u1"
    assert body["user"]["username"] == "alice"


def test_login_invalid_credentials(auth_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = auth_app
    app.dependency_overrides[get_user_repository] = lambda: FakeRepo({"alice": _row()})
    r = tc.post("/auth/login", json={"username": "alice", "password": "wrongpass"})
    assert r.status_code == 401


def test_register_success(auth_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = auth_app
    app.dependency_overrides[get_user_repository] = lambda: FakeRepo({})
    r = tc.post(
        "/auth/register",
        json={
            "username": "bob",
            "password": "password1",
            "confirm_password": "password1",
            "display_name": "Bob",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["success"] is True
    assert body["token_type"] == "bearer"
    assert isinstance(body.get("access_token"), str) and len(body["access_token"]) > 20
    assert body["user"]["username"] == "bob"


def test_login_validation_error_missing_fields(auth_app: tuple[TestClient, FastAPI]) -> None:
    tc, _app = auth_app
    r = tc.post("/auth/login", json={})
    assert r.status_code == 422
    body = r.json()
    assert body.get("error_type") == "RequestValidationError"
    assert body.get("code") == "request_validation_failed"


def test_register_password_mismatch_returns_canonical_400_envelope(
    auth_app: tuple[TestClient, FastAPI],
) -> None:
    tc, app = auth_app
    app.dependency_overrides[get_user_repository] = lambda: FakeRepo({})
    r = tc.post(
        "/auth/register",
        json={
            "username": "bob",
            "password": "password1",
            "confirm_password": "password2",
            "display_name": "Bob",
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body.get("error_type") == "AuthValidationError"
    assert body.get("code") == "auth_validation_failed"
    assert "message" in body


def test_register_conflict(auth_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = auth_app
    app.dependency_overrides[get_user_repository] = lambda: FakeRepo({"alice": _row()})
    r = tc.post(
        "/auth/register",
        json={
            "username": "alice",
            "password": "password1",
            "confirm_password": "password1",
            "display_name": "Alice2",
        },
    )
    assert r.status_code == 409
