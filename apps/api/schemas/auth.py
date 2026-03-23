"""Login/register request and response models (returns bearer token + profile)."""

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
    access_token: str = Field(..., description="JWT for Authorization: Bearer on scoped routes.")
    token_type: str = Field(default="bearer", description="Always ``bearer`` for this API.")
    user: UserMeResponse
