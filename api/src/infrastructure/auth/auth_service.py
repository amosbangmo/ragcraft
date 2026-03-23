import re
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st

from infrastructure.persistence.sqlite.user_repository import SqliteUserRepository
from infrastructure.auth.auth_credentials import try_login, try_register
from infrastructure.auth.password_utils import hash_password, verify_password
from infrastructure.config.paths import get_data_root
from domain.common.ports.password_hasher_port import PasswordHasherPort
from domain.common.ports.user_repository_port import UserRepositoryPort
from infrastructure.persistence.db import init_app_db


DATA_ROOT = get_data_root()
MAX_AVATAR_SIZE_MB = 2
ALLOWED_AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class AuthService:
    SESSION_AUTH_KEY = "is_authenticated"
    SESSION_USER_KEY = "username"
    SESSION_USER_ID_KEY = "user_id"
    SESSION_DISPLAY_NAME_KEY = "display_name"
    SESSION_AVATAR_KEY = "avatar_path"
    SESSION_ACCESS_TOKEN_KEY = "access_token"

    def __init__(
        self,
        user_repository: UserRepositoryPort | None = None,
        *,
        password_hasher: PasswordHasherPort | None = None,
    ):
        init_app_db()
        self.user_repository: UserRepositoryPort = user_repository or SqliteUserRepository()
        if password_hasher is None:
            from infrastructure.auth.bcrypt_password_hasher import BcryptPasswordHasher

            password_hasher = BcryptPasswordHasher()
        self._password_hasher: PasswordHasherPort = password_hasher

    def _set_session(
        self,
        username: str,
        user_id: str,
        display_name: str,
        avatar_path: str | None = None,
    ):
        st.session_state[self.SESSION_AUTH_KEY] = True
        st.session_state[self.SESSION_USER_KEY] = username
        st.session_state[self.SESSION_USER_ID_KEY] = user_id
        st.session_state[self.SESSION_DISPLAY_NAME_KEY] = display_name
        st.session_state[self.SESSION_AVATAR_KEY] = avatar_path

    def _get_user_root(self, user_id: str) -> Path:
        return DATA_ROOT / "users" / user_id

    def _validate_avatar_file(self, uploaded_file) -> tuple[bool, str]:
        if uploaded_file is None:
            return False, "Please choose an image."

        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix not in ALLOWED_AVATAR_EXTENSIONS:
            return False, "Supported formats: PNG, JPG, JPEG, WEBP."

        file_size = getattr(uploaded_file, "size", None)
        if file_size is None:
            uploaded_bytes = uploaded_file.getbuffer()
            file_size = len(uploaded_bytes)

        max_size_bytes = MAX_AVATAR_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"Image is too large. Maximum size is {MAX_AVATAR_SIZE_MB} MB."

        return True, "Avatar file is valid."

    def register(
        self,
        username: str,
        password: str,
        confirm_password: str,
        display_name: str,
    ) -> tuple[bool, str]:
        ok, message, user = try_register(
            self.user_repository,
            username=username,
            password=password,
            confirm_password=confirm_password,
            display_name=display_name,
            password_hasher=self._password_hasher,
        )
        if ok and user:
            self._set_session(
                username=user["username"],
                user_id=user["user_id"],
                display_name=user["display_name"],
                avatar_path=user["avatar_path"],
            )
        return ok, message

    def login(self, username: str, password: str) -> tuple[bool, str]:
        ok, message, user = try_login(
            self.user_repository,
            username,
            password,
            password_hasher=self._password_hasher,
        )
        if ok and user:
            self._set_session(
                username=user["username"],
                user_id=user["user_id"],
                display_name=user["display_name"],
                avatar_path=user["avatar_path"],
            )
        return ok, message

    def logout(self):
        st.session_state[self.SESSION_AUTH_KEY] = False
        st.session_state.pop(self.SESSION_USER_KEY, None)
        st.session_state.pop(self.SESSION_USER_ID_KEY, None)
        st.session_state.pop(self.SESSION_DISPLAY_NAME_KEY, None)
        st.session_state.pop(self.SESSION_AVATAR_KEY, None)
        st.session_state.pop("project_id", None)

    def is_authenticated(self) -> bool:
        return st.session_state.get(self.SESSION_AUTH_KEY, False)

    def get_current_user(self) -> str | None:
        return st.session_state.get(self.SESSION_USER_KEY)

    def get_current_user_id(self) -> str | None:
        return st.session_state.get(self.SESSION_USER_ID_KEY)

    def get_display_name(self) -> str | None:
        return st.session_state.get(self.SESSION_DISPLAY_NAME_KEY)

    def get_current_avatar_path(self) -> str | None:
        return st.session_state.get(self.SESSION_AVATAR_KEY)

    def get_current_user_record(self):
        user_id = self.get_current_user_id()
        if not user_id:
            return None
        return self.user_repository.get_by_user_id(user_id)

    def refresh_session_from_user_id(self, user_id: str) -> bool:
        """Reload session fields from SQLite (e.g. after profile changes via HTTP API)."""
        user = self.user_repository.get_by_user_id(user_id)
        if not user:
            return False
        self._set_session(
            username=user["username"],
            user_id=user["user_id"],
            display_name=user["display_name"],
            avatar_path=user["avatar_path"],
        )
        return True

    def format_created_at(self, created_at: str | None) -> str:
        if not created_at:
            return "-"
        try:
            dt = datetime.fromisoformat(created_at)
            return dt.strftime("%d %b %Y, %H:%M")
        except Exception:
            return created_at

    def update_profile(
        self,
        user_id: str,
        new_username: str,
        new_display_name: str,
    ) -> tuple[bool, str]:
        new_username = new_username.strip().lower()
        new_display_name = new_display_name.strip()

        if not new_username or not new_display_name:
            return False, "Username and display name are required."

        if not re.fullmatch(r"[a-z0-9._-]{3,30}", new_username):
            return False, "Username must be 3-30 chars and contain only letters, numbers, dots, underscores or hyphens."

        current_user = self.user_repository.get_by_user_id(user_id)
        if not current_user:
            return False, "User not found."

        existing_user = self.user_repository.get_by_username(new_username)
        if existing_user and existing_user["user_id"] != user_id:
            return False, "This username is already taken."

        self.user_repository.update_profile(
            user_id=user_id,
            username=new_username,
            display_name=new_display_name,
        )

        updated_user = self.user_repository.get_by_user_id(user_id)

        self._set_session(
            username=updated_user["username"],
            user_id=updated_user["user_id"],
            display_name=updated_user["display_name"],
            avatar_path=updated_user["avatar_path"],
        )

        return True, "Profile updated successfully."

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        confirm_new_password: str,
    ) -> tuple[bool, str]:
        if not current_password or not new_password or not confirm_new_password:
            return False, "All password fields are required."

        if len(new_password) < 8:
            return False, "New password must contain at least 8 characters."

        if new_password != confirm_new_password:
            return False, "New passwords do not match."

        user = self.user_repository.get_by_user_id(user_id)
        if not user:
            return False, "User not found."

        if not verify_password(current_password, user["password_hash"]):
            return False, "Current password is incorrect."

        new_password_hash = hash_password(new_password)
        self.user_repository.update_password(user_id, new_password_hash)

        return True, "Password updated successfully."

    def save_avatar(self, user_id: str, uploaded_file) -> tuple[bool, str]:
        is_valid, message = self._validate_avatar_file(uploaded_file)
        if not is_valid:
            return False, message

        suffix = Path(uploaded_file.name).suffix.lower()
        avatar_dir = self._get_user_root(user_id) / "profile"
        avatar_dir.mkdir(parents=True, exist_ok=True)

        avatar_path = avatar_dir / f"avatar{suffix}"

        for existing in avatar_dir.glob("avatar.*"):
            if existing != avatar_path:
                existing.unlink(missing_ok=True)

        with open(avatar_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        self.user_repository.update_avatar_path(user_id, str(avatar_path))

        user = self.user_repository.get_by_user_id(user_id)
        self._set_session(
            username=user["username"],
            user_id=user["user_id"],
            display_name=user["display_name"],
            avatar_path=user["avatar_path"],
        )

        return True, "Avatar updated successfully."

    def remove_avatar(self, user_id: str) -> tuple[bool, str]:
        user = self.user_repository.get_by_user_id(user_id)
        if not user:
            return False, "User not found."

        avatar_path = user["avatar_path"]
        if avatar_path:
            Path(avatar_path).unlink(missing_ok=True)

        self.user_repository.update_avatar_path(user_id, None)

        updated_user = self.user_repository.get_by_user_id(user_id)
        self._set_session(
            username=updated_user["username"],
            user_id=updated_user["user_id"],
            display_name=updated_user["display_name"],
            avatar_path=updated_user["avatar_path"],
        )

        return True, "Avatar removed successfully."

    def delete_account(self, user_id: str, current_password: str) -> tuple[bool, str]:
        user = self.user_repository.get_by_user_id(user_id)

        if not user:
            return False, "User not found."

        if not current_password:
            return False, "Please enter your current password."

        if not verify_password(current_password, user["password_hash"]):
            return False, "Current password is incorrect."

        self.user_repository.delete_user(user_id)

        user_root = self._get_user_root(user_id)
        if user_root.exists():
            shutil.rmtree(user_root, ignore_errors=True)

        self.logout()

        return True, "Your account has been deleted."
