import streamlit as st

from components.shared.layout import apply_layout
from services import streamlit_auth

st.set_page_config(
    page_title="Login | RAGCraft",
    page_icon="🔐",
    layout="wide",
)

apply_layout(hide_sidebar=True)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 600px;
        margin: 0 auto;
        padding-top: 6vh;
    }

    .login-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 24px;
        padding: 28px 24px 22px 24px;
        box-shadow: 0 12px 32px rgba(15,23,42,0.08);
    }

    .login-logo {
        font-size: 2.2rem;
        text-align: center;
        margin-bottom: 0.5rem;
    }

    .login-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        background: rgba(37,99,235,0.08);
        border: 1px solid rgba(37,99,235,0.16);
        color: #1d4ed8;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0 auto 0.75rem auto;
    }

    .login-title {
        text-align: center;
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f172a;
        margin: 0;
    }

    .login-subtitle {
        text-align: center;
        color: #475569;
        font-size: 0.98rem;
        margin-top: 0.65rem;
        margin-bottom: 1.25rem;
        line-height: 1.5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if streamlit_auth.is_authenticated():
    st.success(f"Already signed in as {streamlit_auth.get_display_name()}.")
    if st.button("Go to Projects", use_container_width=True):
        st.switch_page("pages/projects.py")
    st.stop()

st.markdown(
    """
    <div class="login-card" data-testid="ragcraft-login-shell">
        <div class="login-logo">🔐</div>
        <div style="text-align:center;">
            <div class="login-badge">Authentication</div>
        </div>
        <h1 class="login-title">Welcome to RAGCraft</h1>
        <p class="login-subtitle">
            Sign in or create an account to manage your projects and documents.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_login, tab_signup = st.tabs(["Sign in", "Create account"])

with tab_login:
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Sign in", use_container_width=True, key="login_submit"):
        success, message = streamlit_auth.login(username, password)

        if success:
            st.success(message)
            redirect_page = st.session_state.get("post_login_redirect", "pages/projects.py")
            st.session_state.pop("post_login_redirect", None)
            st.switch_page(redirect_page)
        else:
            st.error(message)

with tab_signup:
    display_name = st.text_input("Display name", key="signup_display_name")
    username = st.text_input("Username", key="signup_username")
    password = st.text_input("Password", type="password", key="signup_password")
    confirm_password = st.text_input(
        "Confirm password", type="password", key="signup_confirm_password"
    )

    if st.button("Create account", use_container_width=True):
        success, message = streamlit_auth.register(
            username=username,
            password=password,
            confirm_password=confirm_password,
            display_name=display_name,
        )

        if success:
            st.success(message)
            st.switch_page("pages/projects.py")
        else:
            st.error(message)
