"""Route-level tests for ``/users`` (dependency overrides, no real SQLite)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.dependencies import get_user_repository
from apps.api.main import create_app
from src.auth.password_utils import hash_password


def _hdr(uid: str = "u1") -> dict[str, str]:
    return {"X-User-Id": uid}


def _sample_row(
    *,
    user_id: str = "u1",
    username: str = "alice",
    display_name: str = "Alice",
    password_plain: str = "oldpass12",
    avatar_path: str | None = None,
) -> dict[str, Any]:
    return {
        "id": 1,
        "username": username,
        "user_id": user_id,
        "password_hash": hash_password(password_plain),
        "display_name": display_name,
        "avatar_path": avatar_path,
        "created_at": "2020-01-01T00:00:00",
    }


class FakeUserRepository:
    """Minimal stand-in for :class:`~src.auth.user_repository.UserRepository`."""

    def __init__(self, row: dict[str, Any] | None, *, username_conflict: dict[str, Any] | None = None):
        self._row = dict(row) if row else None
        self.username_conflict = username_conflict
        self.last_avatar_path: str | None | object = object()
        self.deleted_user_id: str | None = None
        self.password_updates: list[tuple[str, str]] = []

    def get_by_user_id(self, user_id: str):
        if self._row and self._row["user_id"] == user_id:
            return dict(self._row)
        return None

    def get_by_username(self, username: str):
        if self.username_conflict and self.username_conflict.get("username") == username:
            return dict(self.username_conflict)
        if self._row and self._row["username"] == username:
            return dict(self._row)
        return None

    def update_profile(self, user_id: str, username: str, display_name: str) -> None:
        assert self._row is not None
        self._row["username"] = username
        self._row["display_name"] = display_name

    def update_password(self, user_id: str, password_hash: str) -> None:
        assert self._row is not None
        self._row["password_hash"] = password_hash
        self.password_updates.append((user_id, password_hash))

    def update_avatar_path(self, user_id: str, avatar_path: str | None) -> None:
        assert self._row is not None
        self._row["avatar_path"] = avatar_path
        self.last_avatar_path = avatar_path

    def delete_user(self, user_id: str) -> None:
        self.deleted_user_id = user_id
        self._row = None


@pytest.fixture
def users_app() -> tuple[TestClient, FastAPI]:
    app = create_app()
    with TestClient(app) as tc:
        yield tc, app
    app.dependency_overrides.clear()


def test_get_me_missing_header_returns_400(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, _ = users_app
    r = tc.get("/users/me")
    assert r.status_code == 400


def test_get_me_not_found(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = users_app
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(None)
    r = tc.get("/users/me", headers=_hdr())
    assert r.status_code == 404
    assert "not found" in r.json().get("message", "").lower()


def test_get_me_success(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = users_app
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(_sample_row())
    r = tc.get("/users/me", headers=_hdr())
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == "u1"
    assert body["username"] == "alice"
    assert body["display_name"] == "Alice"


def test_patch_me_username_conflict(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = users_app
    conflict = {
        "id": 2,
        "username": "taken",
        "user_id": "other",
        "password_hash": "x",
        "display_name": "Other",
        "avatar_path": None,
        "created_at": None,
    }
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        _sample_row(username="alice"),
        username_conflict=conflict,
    )
    r = tc.patch(
        "/users/me",
        headers=_hdr(),
        json={"username": "taken", "display_name": "Alice A"},
    )
    assert r.status_code == 409


def test_patch_me_invalid_username(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = users_app
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(_sample_row())
    r = tc.patch(
        "/users/me",
        headers=_hdr(),
        json={"username": "ab", "display_name": "Alice"},
    )
    assert r.status_code == 400


def test_patch_me_success(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = users_app
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(_sample_row())
    r = tc.patch(
        "/users/me",
        headers=_hdr(),
        json={"username": "alice_new", "display_name": "Alice B"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["user"]["username"] == "alice_new"
    assert data["user"]["display_name"] == "Alice B"


def test_post_password_wrong_current(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = users_app
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(_sample_row())
    r = tc.post(
        "/users/me/password",
        headers=_hdr(),
        json={
            "current_password": "nopeeeee",
            "new_password": "newpass12",
            "confirm_new_password": "newpass12",
        },
    )
    assert r.status_code == 401


def test_post_password_mismatch(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = users_app
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(_sample_row())
    r = tc.post(
        "/users/me/password",
        headers=_hdr(),
        json={
            "current_password": "oldpass12",
            "new_password": "newpass12",
            "confirm_new_password": "otherthing",
        },
    )
    assert r.status_code == 400


def test_post_password_validation_422(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = users_app
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(_sample_row())
    r = tc.post(
        "/users/me/password",
        headers=_hdr(),
        json={
            "current_password": "oldpass12",
            "new_password": "short",
            "confirm_new_password": "short",
        },
    )
    assert r.status_code == 422


def test_post_password_success(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = users_app
    repo = FakeUserRepository(_sample_row())
    app.dependency_overrides[get_user_repository] = lambda: repo
    r = tc.post(
        "/users/me/password",
        headers=_hdr(),
        json={
            "current_password": "oldpass12",
            "new_password": "newpass123",
            "confirm_new_password": "newpass123",
        },
    )
    assert r.status_code == 200
    assert r.json()["success"] is True
    assert len(repo.password_updates) == 1


def test_post_avatar_rejects_bad_extension(
    users_app: tuple[TestClient, FastAPI],
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tc, app = users_app
    import apps.api.routers.users as users_mod

    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(_sample_row())
    monkeypatch.setattr(users_mod, "DATA_ROOT", tmp_path)
    r = tc.post(
        "/users/me/avatar",
        headers=_hdr(),
        files={"file": ("evil.exe", b"xxxx", "application/octet-stream")},
    )
    assert r.status_code == 400


def test_post_avatar_success(
    users_app: tuple[TestClient, FastAPI],
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tc, app = users_app
    import apps.api.routers.users as users_mod

    repo = FakeUserRepository(_sample_row())
    app.dependency_overrides[get_user_repository] = lambda: repo
    monkeypatch.setattr(users_mod, "DATA_ROOT", tmp_path)
    r = tc.post(
        "/users/me/avatar",
        headers=_hdr(),
        files={"file": ("pic.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert r.status_code == 200
    assert repo.last_avatar_path is not None
    assert isinstance(repo.last_avatar_path, str)
    assert (tmp_path / "users" / "u1" / "profile" / "avatar.png").is_file()


def test_delete_avatar_not_found(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = users_app
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(None)
    r = tc.delete("/users/me/avatar", headers=_hdr())
    assert r.status_code == 404


def test_delete_avatar_clears_db_and_file(
    users_app: tuple[TestClient, FastAPI],
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tc, app = users_app
    import apps.api.routers.users as users_mod

    profile = tmp_path / "users" / "u1" / "profile"
    profile.mkdir(parents=True)
    img = profile / "avatar.png"
    img.write_bytes(b"x")
    row = _sample_row(avatar_path=str(img.resolve()))
    repo = FakeUserRepository(row)
    app.dependency_overrides[get_user_repository] = lambda: repo
    monkeypatch.setattr(users_mod, "DATA_ROOT", tmp_path)
    r = tc.delete("/users/me/avatar", headers=_hdr())
    assert r.status_code == 200
    assert repo.last_avatar_path is None
    assert not img.exists()


def test_delete_me_wrong_password(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, app = users_app
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(_sample_row())
    r = tc.request(
        "DELETE",
        "/users/me",
        headers=_hdr(),
        json={"current_password": "wrongpass1"},
    )
    assert r.status_code == 401


def test_delete_me_success(
    users_app: tuple[TestClient, FastAPI],
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tc, app = users_app
    import apps.api.routers.users as users_mod

    repo = FakeUserRepository(_sample_row())
    app.dependency_overrides[get_user_repository] = lambda: repo
    monkeypatch.setattr(users_mod, "DATA_ROOT", tmp_path)
    root = tmp_path / "users" / "u1"
    root.mkdir(parents=True)
    (root / "marker.txt").write_text("x")
    r = tc.request(
        "DELETE",
        "/users/me",
        headers=_hdr(),
        json={"current_password": "oldpass12"},
    )
    assert r.status_code == 200
    assert repo.deleted_user_id == "u1"
    assert not root.exists()


def test_openapi_lists_users_me(users_app: tuple[TestClient, FastAPI]) -> None:
    tc, _ = users_app
    spec = tc.get("/openapi.json").json()
    assert "/users/me" in spec["paths"]
