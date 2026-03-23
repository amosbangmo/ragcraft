"""Port for persisted application user accounts (SQLite or other stores)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class UserRepositoryPort(Protocol):
    def get_by_username(self, username: str) -> Any: ...

    def get_by_user_id(self, user_id: str) -> Any: ...

    def create_user(
        self, username: str, password_hash: str, display_name: str
    ) -> dict[str, Any]: ...

    def username_exists(self, username: str) -> bool: ...

    def update_profile(self, user_id: str, username: str, display_name: str) -> None: ...

    def update_password(self, user_id: str, password_hash: str) -> None: ...

    def update_avatar_path(self, user_id: str, avatar_path: str | None) -> None: ...

    def delete_user(self, user_id: str) -> None:
        """Remove the user and all persisted rows keyed by ``user_id`` (SQLite adapter cascades)."""
        ...
