from __future__ import annotations

from application.dto.auth import RemoveUserAvatarCommand, RemoveUserAvatarResult
from domain.common.ports.avatar_storage_port import AvatarStoragePort
from domain.common.ports.user_repository_port import UserRepositoryPort
from infrastructure.config.exceptions import UserAccountNotFoundError


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
