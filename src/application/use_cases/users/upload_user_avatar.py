from __future__ import annotations

from src.application.auth.dtos import UploadUserAvatarCommand, UploadUserAvatarResult
from src.application.users.avatar_upload_policy import validate_buffered_avatar_upload
from src.core.exceptions import AuthValidationError, UserAccountNotFoundError
from src.domain.ports.avatar_storage_port import AvatarStoragePort
from src.domain.ports.user_repository_port import UserRepositoryPort


class UploadUserAvatarUseCase:
    def __init__(self, *, users: UserRepositoryPort, avatar_storage: AvatarStoragePort) -> None:
        self._users = users
        self._avatar_storage = avatar_storage

    def execute(self, command: UploadUserAvatarCommand) -> UploadUserAvatarResult:
        user = self._users.get_by_user_id(command.user_id)
        if not user:
            raise UserAccountNotFoundError("user missing", user_message="User not found.")

        try:
            upload = validate_buffered_avatar_upload(command.upload)
        except ValueError as exc:
            raise AuthValidationError(
                f"avatar upload invalid: {exc}",
                user_message=str(exc) or "Invalid avatar upload.",
            ) from exc

        try:
            path = self._avatar_storage.save_avatar(
                user_id=command.user_id,
                upload_filename=upload.source_filename,
                raw=upload.body,
                content_type=upload.declared_media_type,
            )
        except ValueError as exc:
            raise AuthValidationError(
                f"avatar validation failed: {exc}",
                user_message=str(exc) or "Invalid avatar upload.",
            ) from exc

        self._users.update_avatar_path(command.user_id, path)
        return UploadUserAvatarResult(message="Avatar updated successfully.")
