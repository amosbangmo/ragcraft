"""
Account profile UI. Mutations use :class:`~services.protocol.BackendClient`; session fields refresh via
:func:`~services.streamlit_context.refresh_streamlit_auth_session_from_user_id`.
"""

import streamlit as st

from infrastructure.auth.guards import require_authentication
from services.protocol import BackendClient
from services.streamlit_context import refresh_streamlit_auth_session_from_user_id
from components.shared.avatar import render_user_avatar
from components.shared.layout import apply_layout
from components.shared.page_header import render_page_header
from components.shared.section_card import inject_section_card_styles, section_card


require_authentication("pages/profile.py")
apply_layout()


header = render_page_header(
    badge="Profile",
    title="Manage your account",
    subtitle="Update your personal information, avatar and password.",
    show_project_selector=False
)

client: BackendClient = header["backend_client"]
user = client.get_current_user_record()

if user is None:
    st.error("Unable to load user profile.")
    st.stop()

inject_section_card_styles()


@st.dialog("Confirm profile update")
def confirm_profile_update_dialog(user_id: str, username: str, display_name: str):
    st.write("Are you sure you want to update your profile information?")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True, key="cancel_profile_update"):
            st.rerun()

    with col2:
        if st.button("Confirm update", use_container_width=True, key="confirm_profile_update"):
            success, message = client.update_profile(
                user_id=user_id,
                new_username=username,
                new_display_name=display_name,
            )
            if success:
                refresh_streamlit_auth_session_from_user_id(user_id)
                st.session_state["profile_success_message"] = message
            else:
                st.session_state["profile_error_message"] = message
            st.rerun()


@st.dialog("Confirm password change")
def confirm_password_change_dialog(
    user_id: str,
    current_password: str,
    new_password: str,
    confirm_new_password: str,
):
    st.write("Are you sure you want to change your password?")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True, key="cancel_password_change"):
            st.rerun()

    with col2:
        if st.button("Confirm change", use_container_width=True, key="confirm_password_change"):
            success, message = client.change_password(
                user_id=user_id,
                current_password=current_password,
                new_password=new_password,
                confirm_new_password=confirm_new_password,
            )
            if success:
                refresh_streamlit_auth_session_from_user_id(user_id)
                st.session_state["profile_success_message"] = message
            else:
                st.session_state["profile_error_message"] = message
            st.rerun()


@st.dialog("Confirm avatar removal")
def confirm_avatar_removal_dialog(user_id: str):
    st.write("Are you sure you want to remove your avatar?")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True, key="cancel_avatar_removal"):
            st.rerun()

    with col2:
        if st.button("Remove avatar", use_container_width=True, key="confirm_avatar_removal"):
            success, message = client.remove_avatar(user_id)
            if success:
                refresh_streamlit_auth_session_from_user_id(user_id)
                st.session_state["profile_success_message"] = message
            else:
                st.session_state["profile_error_message"] = message
            st.rerun()


@st.dialog("Confirm account deletion")
def confirm_delete_account_dialog(user_id: str, current_password: str):
    st.error("This action is irreversible. Your account and stored user data will be deleted.")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True, key="cancel_delete_account"):
            st.rerun()

    with col2:
        if st.button("Delete account", use_container_width=True, key="confirm_delete_account"):
            success, message = client.delete_account(
                user_id=user_id,
                current_password=current_password,
            )
            if success:
                st.success(message)
                st.switch_page("pages/login.py")
            else:
                st.session_state["profile_error_message"] = message
                st.rerun()

if "profile_success_message" in st.session_state:
    st.success(st.session_state.pop("profile_success_message"))

if "profile_error_message" in st.session_state:
    st.error(st.session_state.pop("profile_error_message"))

row_1_col_1, row_1_col_2 = st.columns(2)
row_2_col_1, row_2_col_2 = st.columns(2)

with row_1_col_1:
    with section_card(
        title="Profile information",
        subtitle="Update your username and display name.",
        min_height=100,
    ):
        new_display_name = st.text_input(
            "Display name",
            value=user["display_name"],
            key="profile_display_name",
        )

        new_username = st.text_input(
            "Username",
            value=user["username"],
            key="profile_username",
        )

        if st.button("Save profile", use_container_width=True):
            confirm_profile_update_dialog(
                user_id=user["user_id"],
                username=new_username,
                display_name=new_display_name,
            )

with row_1_col_2:
    with section_card(
        title="Change password",
        subtitle="Choose a strong password with at least 8 characters.",
        min_height=100,
    ):
        current_password = st.text_input(
            "Current password",
            type="password",
            key="profile_current_password",
        )

        new_password = st.text_input(
            "New password",
            type="password",
            key="profile_new_password",
        )

        confirm_new_password = st.text_input(
            "Confirm new password",
            type="password",
            key="profile_confirm_new_password",
        )

        if st.button("Update password", use_container_width=True):
            confirm_password_change_dialog(
                user_id=user["user_id"],
                current_password=current_password,
                new_password=new_password,
                confirm_new_password=confirm_new_password,
            )

with row_2_col_1:
    with section_card(
        title="Avatar / photo",
        subtitle="Upload a profile image (PNG, JPG, JPEG, WEBP, max 2 MB).",
        min_height=100,
    ):
        render_user_avatar(
            avatar_path=user["avatar_path"],
            display_name=user["display_name"],
            size=140,
        )

        avatar_file = st.file_uploader(
            "Upload avatar",
            type=["png", "jpg", "jpeg", "webp"],
            key="profile_avatar_upload",
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Save avatar", use_container_width=True):
                success, message = client.save_avatar(user["user_id"], avatar_file)
                if success:
                    refresh_streamlit_auth_session_from_user_id(str(user["user_id"]))
                    st.session_state["profile_success_message"] = message
                else:
                    st.session_state["profile_error_message"] = message
                st.rerun()

        with col_b:
            if st.button("Remove avatar", use_container_width=True):
                confirm_avatar_removal_dialog(user["user_id"])

with row_2_col_2:
    with section_card(
        title="Danger zone",
        subtitle="Delete your account after re-authentication.",
        min_height=100,
        danger=True,
    ):
        delete_current_password = st.text_input(
            "Current password to confirm deletion",
            type="password",
            key="profile_delete_password",
        )

        if st.button("Delete account", use_container_width=True):
            confirm_delete_account_dialog(
                user_id=user["user_id"],
                current_password=delete_current_password,
            )

with section_card(
    title="Account details",
    subtitle="Read-only information associated with your account.",
    min_height=100,
):
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Username", user["username"])
    with m2:
        st.metric("Display name", user["display_name"])
    with m3:
        st.metric("User ID", user["user_id"])
    with m4:
        st.metric("Created", client.format_created_at(user["created_at"]))
