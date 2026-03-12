import streamlit as st

from src.core.session import get_user_id
from src.core.app_state import get_app


def render_project_selector(label: str = "Select a project"):
    app = get_app()
    user_id = get_user_id()

    projects = app.list_projects(user_id)

    if not projects:
        st.info("No project available yet. Create one in the Projects page.")
        st.session_state["project_id"] = None
        return None

    current_project_id = st.session_state.get("project_id")

    if current_project_id not in projects:
        current_project_id = projects[0]
        st.session_state["project_id"] = current_project_id

    selected_project = st.selectbox(
        label,
        options=projects,
        index=projects.index(current_project_id),
        key=f"selector_{label}",
    )

    st.session_state["project_id"] = selected_project
    return selected_project