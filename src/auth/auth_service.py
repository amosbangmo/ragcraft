import streamlit as st

from src.auth.password_utils import verify_password


class AuthService:

    SESSION_AUTH_KEY = "is_authenticated"
    SESSION_USER_KEY = "username"
    SESSION_USER_ID_KEY = "user_id"
    SESSION_DISPLAY_NAME_KEY = "display_name"

    def _get_users(self):
        """
        Retrieve users from Streamlit secrets.
        """
        if "users" not in st.secrets:
            return {}

        return st.secrets["users"]

    def login(self, username: str, password: str) -> bool:
        """
        Authenticate a user using credentials stored in st.secrets.
        """

        users = self._get_users()

        if username not in users:
            return False

        user = users[username]
        password_hash = user.get("password_hash")

        if not password_hash:
            return False

        if not verify_password(password, password_hash):
            return False

        # Set session
        st.session_state[self.SESSION_AUTH_KEY] = True
        st.session_state[self.SESSION_USER_KEY] =  user.get("username", username)
        st.session_state[self.SESSION_USER_ID_KEY] = user.get("user_id", username)
        st.session_state[self.SESSION_DISPLAY_NAME_KEY] = user.get("display_name", username)

        return True

    def logout(self):
        """
        Clear authentication session.
        """

        st.session_state[self.SESSION_AUTH_KEY] = False

        st.session_state.pop(self.SESSION_USER_KEY, None)
        st.session_state.pop(self.SESSION_USER_ID_KEY, None)
        st.session_state.pop(self.SESSION_DISPLAY_NAME_KEY, None)
        st.session_state.pop("project_id", None)

    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated.
        """
        return st.session_state.get(self.SESSION_AUTH_KEY, False)

    def get_current_user(self) -> str | None:
        """
        Return username of authenticated user.
        """
        return st.session_state.get(self.SESSION_USER_KEY)

    def get_current_user_id(self) -> str | None:
        """
        Return user_id used in the data layer.
        """
        return st.session_state.get(self.SESSION_USER_ID_KEY)

    def get_display_name(self) -> str | None:
        """
        Return user display name.
        """
        return st.session_state.get(self.SESSION_DISPLAY_NAME_KEY)
