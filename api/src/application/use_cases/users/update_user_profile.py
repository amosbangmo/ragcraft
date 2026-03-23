from __future__ import annotations

from application.auth.username_rules import is_valid_username, normalized_username
from application.dto.auth import (
    UpdateUserProfileCommand,
    UpdateUserProfileResult,
    UserProfileSummary,
)
from domain.common.ports.user_repository_port import UserRepositoryPort
from infrastructure.config.exceptions import (
    AuthValidationError,
    UserAccountNotFoundError,
    UsernameTakenError,
)


class UpdateUserProfileUseCase:
    def __init__(self, *, users: UserRepositoryPort) -> None:
        self._users = users

    def execute(self, command: UpdateUserProfileCommand) -> UpdateUserProfileResult:
        new_username = normalized_username(command.username)
        new_display_name = command.display_name.strip()

        if not new_username or not new_display_name:
            raise AuthValidationError(
                "empty profile fields",
                user_message="Username and display name are required.",
            )

        if not is_valid_username(new_username):
            raise AuthValidationError(
                "invalid username",
                user_message=(
                    "Username must be 3-30 chars and contain only letters, numbers, dots, "
                    "underscores or hyphens."
                ),
            )

        current = self._users.get_by_user_id(command.user_id)
        if not current:
            raise UserAccountNotFoundError("user missing", user_message="User not found.")

        existing = self._users.get_by_username(new_username)
        if existing and str(existing["user_id"]) != command.user_id:
            raise UsernameTakenError(
                "username conflict",
                user_message="This username is already taken.",
            )

        self._users.update_profile(
            user_id=command.user_id,
            username=new_username,
            display_name=new_display_name,
        )
        updated = self._users.get_by_user_id(command.user_id)
        if updated is None:
            raise UserAccountNotFoundError(
                "user missing after update", user_message="User not found."
            )
        profile = UserProfileSummary.from_repository_row(updated)
        return UpdateUserProfileResult(message="Profile updated successfully.", user=profile)
