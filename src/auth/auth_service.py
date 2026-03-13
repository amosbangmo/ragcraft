import re
import streamlit as st

from src.auth.db import init_auth_db
from src.auth.password_utils import hash_password, verify_password
from src.auth.user_repository import UserRepository


class AuthService:
    SESSION_AUTH_KEY = "is_authenticated"
    SESSION_USER_KEY = "username"
    SESSION_USER_ID_KEY = "user_id"
    SESSION_DISPLAY_NAME_KEY = "display_name"

    def __init__(self):
        init_auth_db()
        self.user_repository = UserRepository()

    def _set_session(self, username: str, user_id: str, display_name: str):
        st.session_state[self.SESSION_AUTH_KEY] = True
        st.session_state[self.SESSION_USER_KEY] = username
        st.session_state[self.SESSION_USER_ID_KEY] = user_id
        st.session_state[self.SESSION_DISPLAY_NAME_KEY] = display_name

    def register(
        self,
        username: str,
        password: str,
        confirm_password: str,
        display_name: str,
    ) -> tuple[bool, str]:
        username = username.strip().lower()
        display_name = display_name.strip()

        if not username or not password or not confirm_password or not display_name:
            return False, "All fields are required."

        if not re.fullmatch(r"[a-z0-9._-]{3,30}", username):
            return False, "Username must be 3-30 chars and contain only letters, numbers, dots, underscores or hyphens."

        if len(password) < 8:
            return False, "Password must contain at least 8 characters."

        if password != confirm_password:
            return False, "Passwords do not match."

        if self.user_repository.username_exists(username):
            return False, "This username is already taken."

        password_hash = hash_password(password)

        user = self.user_repository.create_user(
            username=username,
            password_hash=password_hash,
            display_name=display_name,
        )

        self._set_session(
            username=user["username"],
            user_id=user["user_id"],
            display_name=user["display_name"],
        )

        return True, "Account created successfully."

    def login(self, username: str, password: str) -> tuple[bool, str]:
        username = username.strip().lower()

        if not username or not password:
            return False, "Please enter both username and password."

        user = self.user_repository.get_by_username(username)

        if not user:
            return False, "Invalid username or password."

        if not verify_password(password, user["password_hash"]):
            return False, "Invalid username or password."

        self._set_session(
            username=user["username"],
            user_id=user["user_id"],
            display_name=user["display_name"],
        )

        return True, "Login successful."

    def logout(self):
        st.session_state[self.SESSION_AUTH_KEY] = False
        st.session_state.pop(self.SESSION_USER_KEY, None)
        st.session_state.pop(self.SESSION_USER_ID_KEY, None)
        st.session_state.pop(self.SESSION_DISPLAY_NAME_KEY, None)
        st.session_state.pop("project_id", None)

    def is_authenticated(self) -> bool:
        return st.session_state.get(self.SESSION_AUTH_KEY, False)

    def get_current_user(self) -> str | None:
        return st.session_state.get(self.SESSION_USER_KEY)

    def get_current_user_id(self) -> str | None:
        return st.session_state.get(self.SESSION_USER_ID_KEY)

    def get_display_name(self) -> str | None:
        return st.session_state.get(self.SESSION_DISPLAY_NAME_KEY)
