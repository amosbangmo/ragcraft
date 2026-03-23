from __future__ import annotations

from src.application.auth.dtos import RegisterUserCommand, RegisterUserResult, UserProfileSummary
from src.application.auth.username_rules import is_valid_username, normalized_username
from src.core.exceptions import AuthValidationError, UsernameTakenError
from src.domain.ports.password_hasher_port import PasswordHasherPort
from src.domain.ports.user_repository_port import UserRepositoryPort


class RegisterUserUseCase:
    def __init__(self, *, users: UserRepositoryPort, password_hasher: PasswordHasherPort) -> None:
        self._users = users
        self._password_hasher = password_hasher

    def execute(self, command: RegisterUserCommand) -> RegisterUserResult:
        username = normalized_username(command.username)
        display_name = command.display_name.strip()

        if not username or not command.password or not command.confirm_password or not display_name:
            raise AuthValidationError(
                "missing registration fields",
                user_message="All fields are required.",
            )

        if not is_valid_username(username):
            raise AuthValidationError(
                "invalid username format",
                user_message=(
                    "Username must be 3-30 chars and contain only letters, numbers, dots, "
                    "underscores or hyphens."
                ),
            )

        if len(command.password) < 8:
            raise AuthValidationError(
                "password too short",
                user_message="Password must contain at least 8 characters.",
            )

        if command.password != command.confirm_password:
            raise AuthValidationError(
                "password confirm mismatch",
                user_message="Passwords do not match.",
            )

        if self._users.username_exists(username):
            raise UsernameTakenError(
                "username taken",
                user_message="This username is already taken.",
            )

        password_hash = self._password_hasher.hash_password(command.password)
        self._users.create_user(
            username=username,
            password_hash=password_hash,
            display_name=display_name,
        )
        row = self._users.get_by_username(username)
        if not row:
            raise AuthValidationError(
                "create user failed",
                user_message="Account could not be created.",
            )

        profile = UserProfileSummary.from_repository_row(row)
        return RegisterUserResult(message="Account created successfully.", user=profile)
