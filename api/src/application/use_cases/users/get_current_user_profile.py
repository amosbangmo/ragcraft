from __future__ import annotations

from application.dto.auth import GetUserProfileCommand, GetUserProfileResult, UserProfileSummary
from domain.common.ports.user_repository_port import UserRepositoryPort
from infrastructure.config.exceptions import UserAccountNotFoundError


class GetCurrentUserProfileUseCase:
    def __init__(self, *, users: UserRepositoryPort) -> None:
        self._users = users

    def execute(self, command: GetUserProfileCommand) -> GetUserProfileResult:
        row = self._users.get_by_user_id(command.user_id)
        if row is None:
            raise UserAccountNotFoundError("user missing", user_message="User not found.")
        return GetUserProfileResult(user=UserProfileSummary.from_repository_row(row))
