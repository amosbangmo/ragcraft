from __future__ import annotations

from src.application.auth.dtos import RemoveUserAvatarCommand, RemoveUserAvatarResult
from src.core.exceptions import UserAccountNotFoundError
from src.domain.ports.avatar_storage_port import AvatarStoragePort
from src.domain.ports.user_repository_port import UserRepositoryPort


class RemoveUserAvatarUseCase:
    def __init__(self, *, users: UserRepositoryPort, avatar_storage: AvatarStoragePort) -> None:
        self._users = users
        self._avatar_storage = avatar_storage

    def execute(self, command: RemoveUserAvatarCommand) -> RemoveUserAvatarResult:
        user = self._users.get_by_user_id(command.user_id)
        if not user:
            raise UserAccountNotFoundError("user missing", user_message="User not found.")

        self._avatar_storage.remove_avatar_if_stored(command.user_id, user["avatar_path"])
        self._users.update_avatar_path(command.user_id, None)
        return RemoveUserAvatarResult(message="Avatar removed successfully.")
