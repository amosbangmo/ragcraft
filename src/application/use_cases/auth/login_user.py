from __future__ import annotations

from src.application.auth.dtos import LoginUserCommand, LoginUserResult, UserProfileSummary
from src.core.exceptions import AuthCredentialsInvalidError
from src.domain.ports.password_hasher_port import PasswordHasherPort
from src.domain.ports.user_repository_port import UserRepositoryPort


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
