"""
Authenticated user profile API (SQLite).

``X-User-Id`` must match the stored ``user_id`` row. Intended for Streamlit HTTP backend mode
and future SPA clients; login/register remain in Streamlit for now.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Annotated, Any

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
from src.auth.password_utils import hash_password, verify_password
from src.core.paths import get_data_root

router = APIRouter(prefix="/users", tags=["users"])

DATA_ROOT = get_data_root()
_MAX_AVATAR_MB = 2
_ALLOWED_AVATAR_EXT = {".png", ".jpg", ".jpeg", ".webp"}


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
    user_id: Annotated[str, Depends(get_request_user_id)],
    repo: Annotated[Any, Depends(get_user_repository)],
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
    user_id: Annotated[str, Depends(get_request_user_id)],
    repo: Annotated[Any, Depends(get_user_repository)],
) -> ProfileUpdateResponse:
    new_username = body.username.strip().lower()
    new_display_name = body.display_name.strip()
    if not new_username or not new_display_name:
        raise HTTPException(status_code=400, detail="Username and display name are required.")
    if not re.fullmatch(r"[a-z0-9._-]{3,30}", new_username):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-30 chars and contain only letters, numbers, dots, underscores or hyphens.",
        )
    current = repo.get_by_user_id(user_id)
    if not current:
        raise HTTPException(status_code=404, detail="User not found.")
    existing = repo.get_by_username(new_username)
    if existing and str(existing["user_id"]) != user_id:
        raise HTTPException(status_code=400, detail="This username is already taken.")
    repo.update_profile(user_id=user_id, username=new_username, display_name=new_display_name)
    updated = repo.get_by_user_id(user_id)
    u = _row_to_user(updated)
    assert u is not None
    return ProfileUpdateResponse(success=True, message="Profile updated successfully.", user=u)


@router.post("/me/password", response_model=SimpleStatusResponse, summary="Change password")
def post_password(
    body: PasswordChangeRequest,
    user_id: Annotated[str, Depends(get_request_user_id)],
) -> SimpleStatusResponse:
    if not body.current_password or not body.new_password or not body.confirm_new_password:
        raise HTTPException(status_code=400, detail="All password fields are required.")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must contain at least 8 characters.")
    if body.new_password != body.confirm_new_password:
        raise HTTPException(status_code=400, detail="New passwords do not match.")
    user = repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    repo.update_password(user_id, hash_password(body.new_password))
    return SimpleStatusResponse(success=True, message="Password updated successfully.")


def _validate_avatar(upload: UploadFile) -> tuple[bool, str]:
    if upload.filename is None or not str(upload.filename).strip():
        return False, "Please choose an image."
    suffix = Path(upload.filename).suffix.lower()
    if suffix not in _ALLOWED_AVATAR_EXT:
        return False, "Unsupported format. Use PNG, JPG, JPEG, or WEBP."
    return True, ""


@router.post("/me/avatar", response_model=SimpleStatusResponse, summary="Upload avatar image")
async def post_avatar(
    user_id: Annotated[str, Depends(get_request_user_id)],
    repo: Annotated[Any, Depends(get_user_repository)],
    file: UploadFile = File(..., description="PNG, JPG, JPEG, or WEBP (max 2 MB)."),
) -> SimpleStatusResponse:
    ok, msg = _validate_avatar(file)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    raw = await file.read()
    if len(raw) > _MAX_AVATAR_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Avatar exceeds maximum size.")
    suffix = Path(file.filename or "avatar.png").suffix.lower()
    avatar_dir = _user_root(user_id) / "profile"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    avatar_path = avatar_dir / f"avatar{suffix}"
    for existing in avatar_dir.glob("avatar.*"):
        if existing != avatar_path:
            existing.unlink(missing_ok=True)
    avatar_path.write_bytes(raw)
    repo = _repo()
    repo.update_avatar_path(user_id, str(avatar_path))
    return SimpleStatusResponse(success=True, message="Avatar updated successfully.")


@router.delete("/me/avatar", response_model=SimpleStatusResponse, summary="Remove avatar")
def delete_avatar(
    user_id: Annotated[str, Depends(get_request_user_id)],
    repo: Annotated[Any, Depends(get_user_repository)],
) -> SimpleStatusResponse:
    user = repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    ap = user["avatar_path"]
    if ap:
        Path(str(ap)).unlink(missing_ok=True)
    repo.update_avatar_path(user_id, None)
    return SimpleStatusResponse(success=True, message="Avatar removed successfully.")


@router.delete("/me", response_model=SimpleStatusResponse, summary="Delete account")
def delete_me(
    body: DeleteAccountRequest,
    user_id: Annotated[str, Depends(get_request_user_id)],
    repo: Annotated[Any, Depends(get_user_repository)],
) -> SimpleStatusResponse:
    user = repo.get_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if not body.current_password:
        raise HTTPException(status_code=400, detail="Please enter your current password.")
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    repo.delete_user(user_id)
    root = _user_root(user_id)
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    return SimpleStatusResponse(success=True, message="Your account has been deleted.")
