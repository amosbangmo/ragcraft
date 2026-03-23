"""User profile HTTP models (SQLite-backed; routes require a verified bearer JWT)."""

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

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str = Field(..., min_length=8)


class SimpleStatusResponse(BaseModel):
    model_config = {"extra": "forbid"}

    success: bool
    message: str


class DeleteAccountRequest(BaseModel):
    model_config = {"extra": "forbid"}

    current_password: str = Field(..., min_length=1)
