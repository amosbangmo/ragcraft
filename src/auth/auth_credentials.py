"""
SQLite-backed login/register logic shared by :class:`~src.auth.auth_service.AuthService` and tests.

HTTP routes use :class:`~src.application.use_cases.auth.login_user.LoginUserUseCase` instead of calling
this module directly.
"""

from __future__ import annotations

from src.application.auth.dtos import LoginUserCommand, RegisterUserCommand
from src.application.use_cases.auth.login_user import LoginUserUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.core.exceptions import AuthCredentialsInvalidError, AuthValidationError, UsernameTakenError
from src.domain.ports.password_hasher_port import PasswordHasherPort
from src.domain.ports.user_repository_port import UserRepositoryPort


def try_login(
    repo: UserRepositoryPort,
    username: str,
    password: str,
    *,
    password_hasher: PasswordHasherPort,
) -> tuple[bool, str, dict | None]:
    uc = LoginUserUseCase(users=repo, password_hasher=password_hasher)
    try:
        result = uc.execute(LoginUserCommand(username=username, password=password))
    except AuthCredentialsInvalidError as exc:
        return False, exc.user_message, None
    payload = {
        "username": result.user.username,
        "user_id": result.user.user_id,
        "display_name": result.user.display_name,
        "avatar_path": result.user.avatar_path,
        "created_at": result.user.created_at,
    }
    return True, result.message, payload


def try_register(
    repo: UserRepositoryPort,
    *,
    username: str,
    password: str,
    confirm_password: str,
    display_name: str,
    password_hasher: PasswordHasherPort,
) -> tuple[bool, str, dict | None]:
    uc = RegisterUserUseCase(users=repo, password_hasher=password_hasher)
    try:
        result = uc.execute(
            RegisterUserCommand(
                username=username,
                password=password,
                confirm_password=confirm_password,
                display_name=display_name,
            )
        )
    except UsernameTakenError as exc:
        return False, exc.user_message, None
    except AuthValidationError as exc:
        return False, exc.user_message, None
    payload = {
        "username": result.user.username,
        "user_id": result.user.user_id,
        "display_name": result.user.display_name,
        "avatar_path": result.user.avatar_path,
        "created_at": result.user.created_at,
    }
    return True, result.message, payload
