"""User profile and password use cases (in-memory fakes)."""

from __future__ import annotations

from typing import Any

import pytest

from application.dto.auth import (
    ChangeUserPasswordCommand,
    GetUserProfileCommand,
    UpdateUserProfileCommand,
)
from application.use_cases.users.change_user_password import ChangeUserPasswordUseCase
from application.use_cases.users.get_current_user_profile import GetCurrentUserProfileUseCase
from application.use_cases.users.update_user_profile import UpdateUserProfileUseCase
from infrastructure.auth.bcrypt_password_hasher import BcryptPasswordHasher
from infrastructure.config.exceptions import (
    AuthCredentialsInvalidError,
    UserAccountNotFoundError,
    UsernameTakenError,
)


def _row(
    *,
    user_id: str = "u1",
    username: str = "alice",
    password_plain: str = "oldpass12",
) -> dict[str, Any]:
    h = BcryptPasswordHasher()
    return {
        "username": username,
        "user_id": user_id,
        "password_hash": h.hash_password(password_plain),
        "display_name": "Alice",
        "avatar_path": None,
        "created_at": "2020-01-01T00:00:00",
    }


class FakeUsers:
    def __init__(self, row: dict[str, Any] | None):
        self._row = dict(row) if row else None
        self._conflict: dict[str, Any] | None = None

    def set_username_conflict(self, other: dict[str, Any]) -> None:
        self._conflict = dict(other)

    def get_by_user_id(self, user_id: str):
        if self._row and self._row["user_id"] == user_id:
            return dict(self._row)
        return None

    def get_by_username(self, username: str):
        if self._conflict and self._conflict["username"] == username:
            return dict(self._conflict)
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


def test_get_profile_not_found() -> None:
    uc = GetCurrentUserProfileUseCase(users=FakeUsers(None))
    with pytest.raises(UserAccountNotFoundError):
        uc.execute(GetUserProfileCommand(user_id="u1"))


def test_get_profile_ok() -> None:
    uc = GetCurrentUserProfileUseCase(users=FakeUsers(_row()))
    out = uc.execute(GetUserProfileCommand(user_id="u1"))
    assert out.user.username == "alice"


def test_update_profile_username_taken() -> None:
    users = FakeUsers(_row())
    users.set_username_conflict({**_row(), "user_id": "other", "username": "taken"})
    uc = UpdateUserProfileUseCase(users=users)
    with pytest.raises(UsernameTakenError):
        uc.execute(UpdateUserProfileCommand(user_id="u1", username="taken", display_name="Alice A"))


def test_change_password_wrong_current() -> None:
    hasher = BcryptPasswordHasher()
    uc = ChangeUserPasswordUseCase(users=FakeUsers(_row()), password_hasher=hasher)
    with pytest.raises(AuthCredentialsInvalidError):
        uc.execute(
            ChangeUserPasswordCommand(
                user_id="u1",
                current_password="nope",
                new_password="newpass123",
                confirm_new_password="newpass123",
            )
        )


def test_change_password_success() -> None:
    hasher = BcryptPasswordHasher()
    users = FakeUsers(_row())
    uc = ChangeUserPasswordUseCase(users=users, password_hasher=hasher)
    uc.execute(
        ChangeUserPasswordCommand(
            user_id="u1",
            current_password="oldpass12",
            new_password="newpass123",
            confirm_new_password="newpass123",
        )
    )
    assert hasher.verify_password("newpass123", users._row["password_hash"])
