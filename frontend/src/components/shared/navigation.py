import streamlit as st

from services import streamlit_auth
from services.streamlit_context import get_backend_client, get_user_id
from components.shared.avatar import render_user_avatar


def render_navigation(hide_sidebar: bool = False):
    if hide_sidebar:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] {
                display: none;
            }

            [data-testid="stSidebarNav"] {
                display: none;
            }

            header {
                visibility: hidden;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        return

    if streamlit_auth.is_authenticated():
        backend_client = get_backend_client()
        user_id = get_user_id()
        projects = backend_client.list_projects(user_id)
        project_id = st.session_state.get("project_id")
        if not projects:
            st.session_state["project_id"] = None
            project_id = None
        elif not project_id or project_id not in projects:
            project_id = projects[0]
            st.session_state["project_id"] = project_id
    else:
        user_id = None
        project_id = None
        projects = []

    with st.sidebar:
        st.markdown('<div class="nav-title">🚀 RAGCraft</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-subtitle">AI Knowledge Workspace</div>', unsafe_allow_html=True)

        if streamlit_auth.is_authenticated():
            render_user_avatar(
                avatar_path=streamlit_auth.get_current_avatar_path(),
                display_name=streamlit_auth.get_display_name(),
                size=64,
            )
            st.markdown(
                f'<div style="text-align:center;font-weight:600;margin-bottom:30px">{streamlit_auth.get_display_name()}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Not signed in")

        st.page_link("app.py", label="🏠 Home")
        st.page_link("pages/login.py", label="🔐 Login")
        st.page_link("pages/projects.py", label="📁 Projects")
        st.page_link("pages/ingestion.py", label="📄 Ingestion")
        st.page_link("pages/chat.py", label="💬 Chat")
        st.page_link("pages/search.py", label="🔎 Search")
        st.page_link("pages/retrieval_inspector.py", label="🧠 Retrieval Inspector")
        st.page_link("pages/retrieval_comparison.py", label="⚖️ Retrieval Comparison")
        st.page_link("pages/evaluation.py", label="📊 Evaluation")
        st.page_link("pages/settings.py", label="⚙️ Settings")
        st.page_link("pages/profile.py", label="👤 Profile")

        if streamlit_auth.is_authenticated():
            if st.button("Logout", use_container_width=True):
                streamlit_auth.logout()
                st.switch_page("pages/login.py")

        st.markdown("---")

        st.markdown('<div class="sidebar-project-box">', unsafe_allow_html=True)
        st.caption("Current project")

        if project_id:
            st.success(project_id)
        else:
            st.info("No project selected")

        st.caption("Available projects")
        st.markdown(
            f"""
            <div class="sidebar-metric">
                {len(projects)}
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)
