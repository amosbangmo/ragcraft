import streamlit as st

from src.core.session import get_user_id
from src.core.app_state import get_app


def render_project_selector(
    label: str = "Select a project",
    show_create_button: bool = True,
):
    app = get_app()
    user_id = get_user_id()

    projects = app.list_projects(user_id)

    if not projects:

        if show_create_button:

            col_left, col_right = st.columns(
                [5, 1],
                vertical_alignment="center"
            )

            with col_left:
                st.warning(
                    "No project available yet. Create one in the Projects page.",
                    icon="📁"
                )

            with col_right:
                if st.button(
                    "Create project",
                    key=f"create_project_{label}",
                    use_container_width=True
                ):
                    st.switch_page("pages/projects.py")

        else:

            st.warning(
                "No project available yet. Create one in the Projects page.",
                icon="📁"
            )

        st.session_state["project_id"] = None
        return None

    current_project_id = st.session_state.get("project_id")

    if current_project_id not in projects:
        current_project_id = projects[0]
        st.session_state["project_id"] = current_project_id

    # Use key="project_id" so Streamlit updates session state on change before other
    # elements (e.g. sidebar navigation) run in the same script pass.
    selected_project = st.selectbox(
        label,
        options=projects,
        index=projects.index(current_project_id),
        key="project_id",
    )

    return selected_project
