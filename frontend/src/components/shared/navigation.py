import streamlit as st

from components.shared.avatar import render_user_avatar
import services.session.streamlit_auth as streamlit_auth
from services.api_client import get_backend_client
from services.session.streamlit_context import get_user_id


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
        st.markdown(
            '<div class="nav-subtitle">AI Knowledge Workspace</div>', unsafe_allow_html=True
        )

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

        st.markdown('<span data-testid="sidebar-nav-home"></span>', unsafe_allow_html=True)
        st.page_link("app.py", label="🏠 Home")
        st.markdown('<span data-testid="sidebar-nav-login"></span>', unsafe_allow_html=True)
        st.page_link("pages/login.py", label="🔐 Login")
        st.markdown('<span data-testid="sidebar-nav-projects"></span>', unsafe_allow_html=True)
        st.page_link("pages/projects.py", label="📁 Projects")
        st.markdown('<span data-testid="sidebar-nav-ingestion"></span>', unsafe_allow_html=True)
        st.page_link("pages/ingestion.py", label="📄 Ingestion")
        st.markdown('<span data-testid="sidebar-nav-chat"></span>', unsafe_allow_html=True)
        st.page_link("pages/chat.py", label="💬 Chat")
        st.markdown('<span data-testid="sidebar-nav-search"></span>', unsafe_allow_html=True)
        st.page_link("pages/search.py", label="🔎 Search")
        st.markdown('<span data-testid="sidebar-nav-retrieval-inspector"></span>', unsafe_allow_html=True)
        st.page_link("pages/retrieval_inspector.py", label="🧠 Retrieval Inspector")
        st.markdown('<span data-testid="sidebar-nav-retrieval-comparison"></span>', unsafe_allow_html=True)
        st.page_link("pages/retrieval_comparison.py", label="⚖️ Retrieval Comparison")
        st.markdown('<span data-testid="sidebar-nav-evaluation"></span>', unsafe_allow_html=True)
        st.page_link("pages/evaluation.py", label="📊 Evaluation")
        st.markdown(
            '<span data-testid="sidebar-nav-retrieval-settings"></span>', unsafe_allow_html=True
        )
        st.page_link("pages/settings.py", label="⚙️ Settings")
        st.markdown('<span data-testid="sidebar-nav-profile"></span>', unsafe_allow_html=True)
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
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
