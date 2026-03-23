"""Typed contracts for auth and user-profile use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domain.projects.buffered_document_upload import BufferedDocumentUpload


@dataclass(frozen=True, slots=True)
class UserProfileSummary:
    username: str
    user_id: str
    display_name: str
    avatar_path: str | None
    created_at: str | None

    @classmethod
    def from_repository_row(cls, row: Any) -> UserProfileSummary:
        created = row["created_at"]
        return cls(
            username=str(row["username"]),
            user_id=str(row["user_id"]),
            display_name=str(row["display_name"]),
            avatar_path=row["avatar_path"],
            created_at=str(created) if created is not None else None,
        )


@dataclass(frozen=True, slots=True)
class LoginUserCommand:
    username: str
    password: str


@dataclass(frozen=True, slots=True)
class LoginUserResult:
    message: str
    user: UserProfileSummary


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    username: str
    password: str
    confirm_password: str
    display_name: str


@dataclass(frozen=True, slots=True)
class RegisterUserResult:
    message: str
    user: UserProfileSummary


@dataclass(frozen=True, slots=True)
class GetUserProfileCommand:
    user_id: str


@dataclass(frozen=True, slots=True)
class GetUserProfileResult:
    user: UserProfileSummary


@dataclass(frozen=True, slots=True)
class UpdateUserProfileCommand:
    user_id: str
    username: str
    display_name: str


@dataclass(frozen=True, slots=True)
class UpdateUserProfileResult:
    message: str
    user: UserProfileSummary


@dataclass(frozen=True, slots=True)
class ChangeUserPasswordCommand:
    user_id: str
    current_password: str
    new_password: str
    confirm_new_password: str


@dataclass(frozen=True, slots=True)
class ChangeUserPasswordResult:
    message: str


@dataclass(frozen=True, slots=True)
class UploadUserAvatarCommand:
    """Avatar bytes after transport adaptation (:class:`~domain.buffered_document_upload.BufferedDocumentUpload`)."""

    user_id: str
    upload: BufferedDocumentUpload


@dataclass(frozen=True, slots=True)
class UploadUserAvatarResult:
    message: str


@dataclass(frozen=True, slots=True)
class RemoveUserAvatarCommand:
    user_id: str


@dataclass(frozen=True, slots=True)
class RemoveUserAvatarResult:
    message: str


@dataclass(frozen=True, slots=True)
class DeleteUserAccountCommand:
    user_id: str
    current_password: str


@dataclass(frozen=True, slots=True)
class DeleteUserAccountResult:
    message: str
