from __future__ import annotations

from application.dto.auth import LoginUserCommand, LoginUserResult, UserProfileSummary
from domain.common.ports.password_hasher_port import PasswordHasherPort
from domain.common.ports.user_repository_port import UserRepositoryPort
from infrastructure.config.exceptions import AuthCredentialsInvalidError


class LoginUserUseCase:
    def __init__(self, *, users: UserRepositoryPort, password_hasher: PasswordHasherPort) -> None:
        self._users = users
        self._password_hasher = password_hasher

    def execute(self, command: LoginUserCommand) -> LoginUserResult:
        username = command.username.strip().lower()
        if not username or not command.password:
            raise AuthCredentialsInvalidError(
                "missing login fields",
                user_message="Please enter both username and password.",
            )

        user = self._users.get_by_username(username)
        if not user:
            raise AuthCredentialsInvalidError(
                "unknown username",
                user_message="Invalid username or password.",
            )
        if not self._password_hasher.verify_password(command.password, user["password_hash"]):
            raise AuthCredentialsInvalidError(
                "password mismatch",
                user_message="Invalid username or password.",
            )

        profile = UserProfileSummary.from_repository_row(user)
        return LoginUserResult(message="Login successful.", user=profile)
