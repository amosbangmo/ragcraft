import streamlit as st

from src.core.session import get_user_id
from src.core.app_state import get_app


def render_navigation():
    app = get_app()
    user_id = get_user_id()
    project_id = st.session_state.get("project_id")
    projects = app.list_projects(user_id)

    with st.sidebar:
        st.markdown('<div class="nav-title">🚀 RAGCraft</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-subtitle">AI Knowledge Workspace</div>', unsafe_allow_html=True)

        st.page_link("streamlit_app.py", label="🏠 Home")
        st.page_link("pages/projects.py", label="📁 Projects")
        st.page_link("pages/ingestion.py", label="📄 Ingestion")
        st.page_link("pages/chat.py", label="💬 Chat")
        st.page_link("pages/search.py", label="🔎 Search")
        st.page_link("pages/evaluation.py", label="📊 Evaluation")

        st.markdown("---")

        st.markdown('<div class="sidebar-project-box">', unsafe_allow_html=True)
        st.caption("Current project")
        if project_id:
            st.success(project_id)
        else:
            st.info("No project selected")

        st.caption("Available projects")
        st.write(len(projects))
        st.markdown("</div>", unsafe_allow_html=True)