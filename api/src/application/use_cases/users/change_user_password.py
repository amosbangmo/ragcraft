from __future__ import annotations

from application.dto.auth import ChangeUserPasswordCommand, ChangeUserPasswordResult
from domain.common.ports.password_hasher_port import PasswordHasherPort
from domain.common.ports.user_repository_port import UserRepositoryPort
from infrastructure.config.exceptions import (
    AuthCredentialsInvalidError,
    AuthValidationError,
    UserAccountNotFoundError,
)


class ChangeUserPasswordUseCase:
    def __init__(self, *, users: UserRepositoryPort, password_hasher: PasswordHasherPort) -> None:
        self._users = users
        self._password_hasher = password_hasher

    def execute(self, command: ChangeUserPasswordCommand) -> ChangeUserPasswordResult:
        if command.new_password != command.confirm_new_password:
            raise AuthValidationError(
                "new password mismatch",
                user_message="New passwords do not match.",
            )

        user = self._users.get_by_user_id(command.user_id)
        if not user:
            raise UserAccountNotFoundError("user missing", user_message="User not found.")

        if not self._password_hasher.verify_password(
            command.current_password, user["password_hash"]
        ):
            raise AuthCredentialsInvalidError(
                "wrong current password",
                user_message="Current password is incorrect.",
            )

        self._users.update_password(
            command.user_id, self._password_hasher.hash_password(command.new_password)
        )
        return ChangeUserPasswordResult(message="Password updated successfully.")
