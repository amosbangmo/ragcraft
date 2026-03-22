"""Login/register request and response models (no ``X-User-Id``; used before session exists)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from apps.api.schemas.users import UserMeResponse


class LoginRequest(BaseModel):
    model_config = {"extra": "forbid"}

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    model_config = {"extra": "forbid"}

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1)


class AuthSuccessResponse(BaseModel):
    model_config = {"extra": "forbid"}

    success: bool = True
    message: str
    user: UserMeResponse
