"""
Authenticated user profile API (SQLite).

The JWT ``user_id`` claim must match the stored ``user_id`` row. Used by HTTP ``HttpBackendClient``
and SPA clients after ``/auth/login`` or ``/auth/register``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from application.dto.auth import (
    ChangeUserPasswordCommand,
    DeleteUserAccountCommand,
    GetUserProfileCommand,
    RemoveUserAvatarCommand,
    UpdateUserProfileCommand,
    UploadUserAvatarCommand,
)
from application.use_cases.users.change_user_password import ChangeUserPasswordUseCase
from application.use_cases.users.delete_user_account import DeleteUserAccountUseCase
from application.use_cases.users.get_current_user_profile import GetCurrentUserProfileUseCase
from application.use_cases.users.remove_user_avatar import RemoveUserAvatarUseCase
from application.use_cases.users.update_user_profile import UpdateUserProfileUseCase
from application.use_cases.users.upload_user_avatar import UploadUserAvatarUseCase
from domain.auth.authenticated_principal import AuthenticatedPrincipal
from interfaces.http.dependencies import (
    get_authenticated_principal,
    get_change_user_password_use_case,
    get_delete_user_account_use_case,
    get_get_current_user_profile_use_case,
    get_remove_user_avatar_use_case,
    get_update_user_profile_use_case,
    get_upload_user_avatar_use_case,
)
from interfaces.http.schemas.mappers import user_profile_summary_to_me
from interfaces.http.schemas.users import (
    DeleteAccountRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    ProfileUpdateResponse,
    SimpleStatusResponse,
    UserMeResponse,
)
from interfaces.http.upload_adapter import (
    StarletteUploadPayloadError,
    StarletteUploadTooLargeError,
    read_buffered_avatar_upload,
)

router = APIRouter(prefix="/users", tags=["users"])

PrincipalDep = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
GetProfileUCDep = Annotated[
    GetCurrentUserProfileUseCase, Depends(get_get_current_user_profile_use_case)
]
UpdateProfileUCDep = Annotated[UpdateUserProfileUseCase, Depends(get_update_user_profile_use_case)]
ChangePasswordUCDep = Annotated[
    ChangeUserPasswordUseCase, Depends(get_change_user_password_use_case)
]
UploadAvatarUCDep = Annotated[UploadUserAvatarUseCase, Depends(get_upload_user_avatar_use_case)]
RemoveAvatarUCDep = Annotated[RemoveUserAvatarUseCase, Depends(get_remove_user_avatar_use_case)]
DeleteAccountUCDep = Annotated[DeleteUserAccountUseCase, Depends(get_delete_user_account_use_case)]


@router.get("/me", response_model=UserMeResponse, summary="Current user profile (from bearer JWT)")
def get_me(principal: PrincipalDep, use_case: GetProfileUCDep) -> UserMeResponse:
    result = use_case.execute(GetUserProfileCommand(user_id=principal.user_id))
    return user_profile_summary_to_me(result.user)


@router.patch(
    "/me", response_model=ProfileUpdateResponse, summary="Update username and display name"
)
def patch_me(
    body: ProfileUpdateRequest,
    principal: PrincipalDep,
    use_case: UpdateProfileUCDep,
) -> ProfileUpdateResponse:
    result = use_case.execute(
        UpdateUserProfileCommand(
            user_id=principal.user_id,
            username=body.username,
            display_name=body.display_name,
        )
    )
    return ProfileUpdateResponse(
        success=True,
        message=result.message,
        user=user_profile_summary_to_me(result.user),
    )


@router.post("/me/password", response_model=SimpleStatusResponse, summary="Change password")
def post_password(
    body: PasswordChangeRequest,
    principal: PrincipalDep,
    use_case: ChangePasswordUCDep,
) -> SimpleStatusResponse:
    result = use_case.execute(
        ChangeUserPasswordCommand(
            user_id=principal.user_id,
            current_password=body.current_password,
            new_password=body.new_password,
            confirm_new_password=body.confirm_new_password,
        )
    )
    return SimpleStatusResponse(success=True, message=result.message)


@router.post(
    "/me/avatar",
    response_model=SimpleStatusResponse,
    summary="Upload avatar image",
    responses={
        400: {"description": "Invalid or unreadable upload"},
        413: {"description": "Avatar larger than RAG_MAX_AVATAR_UPLOAD_BYTES"},
    },
)
async def post_avatar(
    principal: PrincipalDep,
    use_case: UploadAvatarUCDep,
    file: UploadFile = File(..., description="PNG, JPG, JPEG, or WEBP (max 2 MB)."),
) -> SimpleStatusResponse:
    """
    Multipart field ``file`` is read in chunks up to ``RAG_MAX_AVATAR_UPLOAD_BYTES`` (default 2 MiB),
    same policy as document ingest (see ``interfaces.http.upload_adapter``).
    """
    try:
        upload = await read_buffered_avatar_upload(file)
    except StarletteUploadTooLargeError as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc
    except StarletteUploadPayloadError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    result = use_case.execute(
        UploadUserAvatarCommand(
            user_id=principal.user_id,
            upload=upload,
        )
    )
    return SimpleStatusResponse(success=True, message=result.message)


@router.delete("/me/avatar", response_model=SimpleStatusResponse, summary="Remove avatar")
def delete_avatar(principal: PrincipalDep, use_case: RemoveAvatarUCDep) -> SimpleStatusResponse:
    result = use_case.execute(RemoveUserAvatarCommand(user_id=principal.user_id))
    return SimpleStatusResponse(success=True, message=result.message)


@router.delete(
    "/me",
    response_model=SimpleStatusResponse,
    summary="Delete account and all user-owned data",
)
def delete_me(
    body: DeleteAccountRequest,
    principal: PrincipalDep,
    use_case: DeleteAccountUCDep,
) -> SimpleStatusResponse:
    """
    Verifies the current password, then deletes every DB row for this ``user_id`` (users,
    rag_assets, qa_dataset, query_logs, project_retrieval_settings) and removes
    ``<data_root>/users/<user_id>`` on disk (projects, indexes, avatars).
    """
    result = use_case.execute(
        DeleteUserAccountCommand(user_id=principal.user_id, current_password=body.current_password)
    )
    return SimpleStatusResponse(success=True, message=result.message)
