from __future__ import annotations

from src.application.auth.dtos import GetUserProfileCommand, GetUserProfileResult, UserProfileSummary
from src.core.exceptions import UserAccountNotFoundError
from src.domain.ports.user_repository_port import UserRepositoryPort


class GetCurrentUserProfileUseCase:
    def __init__(self, *, users: UserRepositoryPort) -> None:
        self._users = users

    def execute(self, command: GetUserProfileCommand) -> GetUserProfileResult:
        row = self._users.get_by_user_id(command.user_id)
        if row is None:
            raise UserAccountNotFoundError("user missing", user_message="User not found.")
        return GetUserProfileResult(user=UserProfileSummary.from_repository_row(row))
