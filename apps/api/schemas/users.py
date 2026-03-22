"""User profile HTTP models (SQLite-backed, ``X-User-Id`` scoped)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserMeResponse(BaseModel):
    model_config = {"extra": "forbid"}

    username: str
    user_id: str
    display_name: str
    avatar_path: str | None = None
    created_at: str | None = None


class ProfileUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    username: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)


class ProfileUpdateResponse(BaseModel):
    model_config = {"extra": "forbid"}

    success: bool
    message: str
    user: UserMeResponse


class PasswordChangeRequest(BaseModel):
    model_config = {"extra": "forbid"}

    current_password: str
    new_password: str
    confirm_new_password: str


class SimpleStatusResponse(BaseModel):
    model_config = {"extra": "forbid"}

    success: bool
    message: str


class DeleteAccountRequest(BaseModel):
    model_config = {"extra": "forbid"}

    current_password: str
