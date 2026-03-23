"""Application-layer login and registration (ports + DTOs)."""

from __future__ import annotations

from typing import Any

import pytest

from application.dto.auth import LoginUserCommand, RegisterUserCommand
from application.use_cases.auth.login_user import LoginUserUseCase
from application.use_cases.auth.register_user import RegisterUserUseCase
from infrastructure.config.exceptions import AuthCredentialsInvalidError, AuthValidationError, UsernameTakenError
from infrastructure.auth.bcrypt_password_hasher import BcryptPasswordHasher


def _row(
    *,
    user_id: str = "u1",
    username: str = "alice",
    display_name: str = "Alice",
    password_plain: str = "secret123",
) -> dict[str, Any]:
    hasher = BcryptPasswordHasher()
    return {
        "id": 1,
        "username": username,
        "user_id": user_id,
        "password_hash": hasher.hash_password(password_plain),
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


def test_login_success() -> None:
    hasher = BcryptPasswordHasher()
    repo = FakeRepo({"alice": _row()})
    uc = LoginUserUseCase(users=repo, password_hasher=hasher)
    out = uc.execute(LoginUserCommand(username="alice", password="secret123"))
    assert out.user.user_id == "u1"
    assert "successful" in out.message.lower()


def test_login_rejects_bad_password() -> None:
    hasher = BcryptPasswordHasher()
    repo = FakeRepo({"alice": _row()})
    uc = LoginUserUseCase(users=repo, password_hasher=hasher)
    with pytest.raises(AuthCredentialsInvalidError):
        uc.execute(LoginUserCommand(username="alice", password="wrong"))


def test_register_rejects_mismatched_passwords() -> None:
    hasher = BcryptPasswordHasher()
    uc = RegisterUserUseCase(users=FakeRepo({}), password_hasher=hasher)
    with pytest.raises(AuthValidationError, match="match"):
        uc.execute(
            RegisterUserCommand(
                username="bob",
                password="password1",
                confirm_password="password2",
                display_name="Bob",
            )
        )


def test_register_conflict() -> None:
    hasher = BcryptPasswordHasher()
    repo = FakeRepo({"alice": _row()})
    uc = RegisterUserUseCase(users=repo, password_hasher=hasher)
    with pytest.raises(UsernameTakenError):
        uc.execute(
            RegisterUserCommand(
                username="alice",
                password="password1",
                confirm_password="password1",
                display_name="Alice2",
            )
        )
