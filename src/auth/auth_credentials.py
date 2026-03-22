"""
SQLite-backed login/register logic shared by :class:`~src.auth.auth_service.AuthService` and the HTTP API.

No Streamlit imports — safe for FastAPI routers and tests.
"""

from __future__ import annotations

import re

from src.auth.password_utils import hash_password, verify_password
from src.auth.user_repository import UserRepository


def _session_payload_from_row(row) -> dict:
    created = row["created_at"]
    return {
        "username": str(row["username"]),
        "user_id": str(row["user_id"]),
        "display_name": str(row["display_name"]),
        "avatar_path": row["avatar_path"],
        "created_at": str(created) if created is not None else None,
    }


def try_login(
    repo: UserRepository,
    username: str,
    password: str,
) -> tuple[bool, str, dict | None]:
    username = username.strip().lower()
    if not username or not password:
        return False, "Please enter both username and password.", None

    user = repo.get_by_username(username)
    if not user:
        return False, "Invalid username or password.", None
    if not verify_password(password, user["password_hash"]):
        return False, "Invalid username or password.", None

    return True, "Login successful.", _session_payload_from_row(user)


def try_register(
    repo: UserRepository,
    *,
    username: str,
    password: str,
    confirm_password: str,
    display_name: str,
) -> tuple[bool, str, dict | None]:
    username = username.strip().lower()
    display_name = display_name.strip()

    if not username or not password or not confirm_password or not display_name:
        return False, "All fields are required.", None

    if not re.fullmatch(r"[a-z0-9._-]{3,30}", username):
        return (
            False,
            "Username must be 3-30 chars and contain only letters, numbers, dots, underscores or hyphens.",
            None,
        )

    if len(password) < 8:
        return False, "Password must contain at least 8 characters.", None

    if password != confirm_password:
        return False, "Passwords do not match.", None

    if repo.username_exists(username):
        return False, "This username is already taken.", None

    password_hash = hash_password(password)
    repo.create_user(
        username=username,
        password_hash=password_hash,
        display_name=display_name,
    )
    row = repo.get_by_username(username)
    if not row:
        return False, "Account could not be created.", None
    return True, "Account created successfully.", _session_payload_from_row(row)
