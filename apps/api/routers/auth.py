"""
Pre-session authentication (login/register) for SPA and Streamlit HTTP backend mode.

These routes do not use ``X-User-Id``; they validate credentials against the same SQLite store as
``/users/me`` endpoints.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.dependencies import get_user_repository
from apps.api.schemas.auth import AuthSuccessResponse, LoginRequest, RegisterRequest
from apps.api.schemas.users import UserMeResponse
from src.auth.auth_credentials import try_login, try_register
from src.auth.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])

UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def _to_me(user: dict) -> UserMeResponse:
    return UserMeResponse(
        username=str(user["username"]),
        user_id=str(user["user_id"]),
        display_name=str(user["display_name"]),
        avatar_path=user["avatar_path"],
        created_at=user.get("created_at"),
    )


@router.post(
    "/login",
    response_model=AuthSuccessResponse,
    summary="Sign in (returns profile for client-side session)",
)
def post_login(
    body: LoginRequest,
    repo: UserRepositoryDep,
) -> AuthSuccessResponse:
    ok, message, user = try_login(repo, body.username, body.password)
    if not ok or not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
    return AuthSuccessResponse(message=message, user=_to_me(user))


@router.post(
    "/register",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create account (returns profile for client-side session)",
)
def post_register(
    body: RegisterRequest,
    repo: UserRepositoryDep,
) -> AuthSuccessResponse:
    ok, message, user = try_register(
        repo,
        username=body.username,
        password=body.password,
        confirm_password=body.confirm_password,
        display_name=body.display_name,
    )
    if not ok or not user:
        if "taken" in message.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return AuthSuccessResponse(message=message, user=_to_me(user))
