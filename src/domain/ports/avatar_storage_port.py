"""Port for avatar files and per-user workspace cleanup (no FastAPI / HTTP types)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AvatarStoragePort(Protocol):
    def save_avatar(
        self,
        *,
        user_id: str,
        upload_filename: str | None,
        raw: bytes,
        content_type: str | None,
    ) -> str:
        """Persist validated image bytes; return stored path string for the repository."""

    def remove_avatar_if_stored(self, user_id: str, avatar_path_str: str | None) -> None:
        """Delete file on disk when it belongs to this user's tree."""

    def delete_user_data_tree(self, user_id: str) -> None:
        """Remove ``<data_root>/users/<user_id>`` after account deletion."""
