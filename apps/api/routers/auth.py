"""
Pre-session authentication (login/register) for SPA and Streamlit HTTP backend mode.

These routes do not use ``X-User-Id``; they delegate to application use cases backed by the same
SQLite store as ``/users/me``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from apps.api.dependencies import get_login_user_use_case, get_register_user_use_case
from apps.api.schemas.auth import AuthSuccessResponse, LoginRequest, RegisterRequest
from apps.api.schemas.mappers import user_profile_summary_to_me
from src.application.auth.dtos import LoginUserCommand, RegisterUserCommand
from src.application.use_cases.auth.login_user import LoginUserUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase

router = APIRouter(prefix="/auth", tags=["auth"])

LoginUserUCDep = Annotated[LoginUserUseCase, Depends(get_login_user_use_case)]
RegisterUserUCDep = Annotated[RegisterUserUseCase, Depends(get_register_user_use_case)]


@router.post(
    "/login",
    response_model=AuthSuccessResponse,
    summary="Sign in (returns profile for client-side session)",
)
def post_login(body: LoginRequest, use_case: LoginUserUCDep) -> AuthSuccessResponse:
    result = use_case.execute(LoginUserCommand(username=body.username, password=body.password))
    return AuthSuccessResponse(message=result.message, user=user_profile_summary_to_me(result.user))


@router.post(
    "/register",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create account (returns profile for client-side session)",
)
def post_register(body: RegisterRequest, use_case: RegisterUserUCDep) -> AuthSuccessResponse:
    result = use_case.execute(
        RegisterUserCommand(
            username=body.username,
            password=body.password,
            confirm_password=body.confirm_password,
            display_name=body.display_name,
        )
    )
    return AuthSuccessResponse(message=result.message, user=user_profile_summary_to_me(result.user))
