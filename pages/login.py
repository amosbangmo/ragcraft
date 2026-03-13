import streamlit as st

from src.ui.layout import apply_layout
from src.auth.auth_service import AuthService


# -------------------------
# Page setup
# -------------------------
st.set_page_config(
    page_title="Login | RAGCraft",
    page_icon="🔐",
    layout="wide",
)

apply_layout(hide_sidebar=True)

st.markdown(
    """
    <style>
    /* Center the login page content */
    .block-container {
        max-width: 600px;
        margin: 0 auto;
        padding-top: 6vh;
    }

    .login-shell {
        display: flex;
        flex-direction: column;
        gap: 1rem;
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

    .login-footer {
        text-align: center;
        color: #64748b;
        font-size: 0.85rem;
        margin-top: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

auth_service = AuthService()

# -------------------------
# Already authenticated
# -------------------------
if auth_service.is_authenticated():
    st.markdown(
        """
        <div class="login-shell">
            <div class="login-card">
                <div class="login-logo">🚀</div>
                <div style="text-align:center;">
                    <div class="login-badge">Authentication</div>
                </div>
                <h1 class="login-title">Welcome back</h1>
                <p class="login-subtitle">
                    You are already signed in to RAGCraft.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.success(f"Signed in as {auth_service.get_display_name()}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Go to Projects", use_container_width=True):
            st.switch_page("pages/projects.py")
    with col2:
        if st.button("Logout", use_container_width=True):
            auth_service.logout()
            st.rerun()

    st.stop()

# -------------------------
# Login form
# -------------------------
st.markdown(
    """
    <div class="login-shell">
        <div class="login-card">
            <div class="login-logo">🔐</div>
            <div style="text-align:center;">
                <div class="login-badge">Authentication</div>
            </div>
            <h1 class="login-title">Sign in to RAGCraft</h1>
            <p class="login-subtitle">
                Access your projects, ingested documents and conversational workspace.
            </p>
    """,
    unsafe_allow_html=True,
)

username = st.text_input(
    "Username",
    placeholder="Enter your username",
)

password = st.text_input(
    "Password",
    type="password",
    placeholder="Enter your password",
)

signin_clicked = st.button("Sign in", use_container_width=True)

if signin_clicked:
    if not username.strip() or not password.strip():
        st.warning("Please enter both username and password.")
    else:
        success = auth_service.login(username.strip(), password)

        if success:
            st.success("Login successful.")
            redirect_page = st.session_state.get("post_login_redirect", "pages/projects.py")
            st.session_state.pop("post_login_redirect", None)
            st.switch_page(redirect_page)
        else:
            st.error("Invalid username or password.")

st.markdown(
    """
            <div class="login-footer">
                Local authentication enabled for this workspace
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
