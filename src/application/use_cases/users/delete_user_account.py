from __future__ import annotations

from src.application.auth.dtos import DeleteUserAccountCommand, DeleteUserAccountResult
from src.core.exceptions import AuthCredentialsInvalidError, UserAccountNotFoundError
from src.domain.ports.avatar_storage_port import AvatarStoragePort
from src.domain.ports.password_hasher_port import PasswordHasherPort
from src.domain.ports.user_repository_port import UserRepositoryPort


class DeleteUserAccountUseCase:
    def __init__(
        self,
        *,
        users: UserRepositoryPort,
        password_hasher: PasswordHasherPort,
        avatar_storage: AvatarStoragePort,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._avatar_storage = avatar_storage

    def execute(self, command: DeleteUserAccountCommand) -> DeleteUserAccountResult:
        user = self._users.get_by_user_id(command.user_id)
        if not user:
            raise UserAccountNotFoundError("user missing", user_message="User not found.")

        if not self._password_hasher.verify_password(command.current_password, user["password_hash"]):
            raise AuthCredentialsInvalidError(
                "wrong password for delete",
                user_message="Current password is incorrect.",
            )

        self._users.delete_user(command.user_id)
        self._avatar_storage.delete_user_data_tree(command.user_id)
        return DeleteUserAccountResult(message="Your account has been deleted.")
