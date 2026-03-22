"""
Authenticated user profile API (SQLite).

``X-User-Id`` must match the stored ``user_id`` row. Used by HTTP ``BackendClient`` and future
SPA clients; interactive login/register may remain hosted outside this API until auth is unified.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from apps.api.dependencies import get_request_user_id, get_user_repository
from apps.api.schemas.users import (
    DeleteAccountRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    ProfileUpdateResponse,
    SimpleStatusResponse,
    UserMeResponse,
)
from apps.api.user_avatar_io import (
    avatar_suffix_from_upload_filename,
    safe_remove_stored_avatar_file,
    write_avatar_bytes,
)
from src.auth.password_utils import hash_password, verify_password
from src.auth.user_repository import UserRepository
from src.core.paths import get_data_root

router = APIRouter(prefix="/users", tags=["users"])

DATA_ROOT = get_data_root()

UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
RequestUserIdDep = Annotated[str, Depends(get_request_user_id)]


def _row_to_user(row) -> UserMeResponse | None:
    if row is None:
        return None
    return UserMeResponse(
        username=str(row["username"]),
        user_id=str(row["user_id"]),
        display_name=str(row["display_name"]),
        avatar_path=row["avatar_path"],
        created_at=str(row["created_at"]) if row["created_at"] is not None else None,
    )


def _user_root(user_id: str) -> Path:
    return DATA_ROOT / "users" / user_id


@router.get("/me", response_model=UserMeResponse, summary="Current user profile (by X-User-Id)")
def get_me(
    user_id: RequestUserIdDep,
    repo: UserRepositoryDep,
) -> UserMeResponse:
    row = repo.get_by_user_id(user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    u = _row_to_user(row)
    assert u is not None
    return u


@router.patch("/me", response_model=ProfileUpdateResponse, summary="Update username and display name")
def patch_me(
    body: ProfileUpdateRequest,
    user_id: RequestUserIdDep,
    repo: UserRepositoryDep,
) -> ProfileUpdateResponse:
    new_username = body.username.strip().lower()
    new_display_name = body.display_name.strip()
    if not new_username or not new_display_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and display name are required.",
        )
    if not re.fullmatch(r"[a-z0-9._-]{3,30}", new_username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be 3-30 chars and contain only letters, numbers, dots, underscores or hyphens.",
        )
    current = repo.get_by_user_id(user_id)
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    existing = repo.get_by_username(new_username)
    if existing and str(existing["user_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken.",
        )
    repo.update_profile(user_id=user_id, username=new_username, display_name=new_display_name)
    updated = repo.get_by_user_id(user_id)
    u = _row_to_user(updated)
    assert u is not None
    return ProfileUpdateResponse(success=True, message="Profile updated successfully.", user=u)


@router.post("/me/password", response_model=SimpleStatusResponse, summary="Change password")
def post_password(
    body: PasswordChangeRequest,
    user_id: RequestUserIdDep,
    repo: UserRepositoryDep,
) -> SimpleStatusResponse:
    if body.new_password != body.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match.",
        )
    user = repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )
    repo.update_password(user_id, hash_password(body.new_password))
    return SimpleStatusResponse(success=True, message="Password updated successfully.")


@router.post("/me/avatar", response_model=SimpleStatusResponse, summary="Upload avatar image")
async def post_avatar(
    user_id: RequestUserIdDep,
    repo: UserRepositoryDep,
    file: UploadFile = File(..., description="PNG, JPG, JPEG, or WEBP (max 2 MB)."),
) -> SimpleStatusResponse:
    try:
        suffix = avatar_suffix_from_upload_filename(file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raw = await file.read()
    try:
        avatar_path = write_avatar_bytes(
            data_root=DATA_ROOT,
            user_id=user_id,
            suffix=suffix,
            raw=raw,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    repo.update_avatar_path(user_id, str(avatar_path))
    return SimpleStatusResponse(success=True, message="Avatar updated successfully.")


@router.delete("/me/avatar", response_model=SimpleStatusResponse, summary="Remove avatar")
def delete_avatar(
    user_id: RequestUserIdDep,
    repo: UserRepositoryDep,
) -> SimpleStatusResponse:
    user = repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    safe_remove_stored_avatar_file(
        data_root=DATA_ROOT,
        user_id=user_id,
        avatar_path_str=user["avatar_path"],
    )
    repo.update_avatar_path(user_id, None)
    return SimpleStatusResponse(success=True, message="Avatar removed successfully.")


@router.delete("/me", response_model=SimpleStatusResponse, summary="Delete account")
def delete_me(
    body: DeleteAccountRequest,
    user_id: RequestUserIdDep,
    repo: UserRepositoryDep,
) -> SimpleStatusResponse:
    user = repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )
    repo.delete_user(user_id)
    root = _user_root(user_id)
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    return SimpleStatusResponse(success=True, message="Your account has been deleted.")
