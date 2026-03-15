import streamlit as st

from src.core.app_state import get_app
from src.core.session import get_user_id
from src.ui.project_selector import render_project_selector


def render_hero(title: str, subtitle: str, badge: str):
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-badge">{badge}</div>
            <h1 class="hero-title">{title}</h1>
            <p class="hero-subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(metrics: list[tuple[str, str | int | float]]):
    if not metrics:
        return

    columns = st.columns(len(metrics))

    for col, (label, value) in zip(columns, metrics):
        with col:
            st.metric(label, value)


def render_page_header(
    *,
    badge: str,
    title: str,
    subtitle: str,
    selector_label: str = "Select a project",
    show_project_selector: bool = True,
    show_refresh_button: bool = False,
    show_create_button_when_empty: bool = True,
    refresh_button_label: str = "🔄 Refresh chain",
    refresh_button_disabled: bool = False,
    metrics: list[tuple[str, str | int | float]] | None = None,
):
    app = get_app()
    user_id = get_user_id()

    render_hero(
        title=title,
        subtitle=subtitle,
        badge=badge,
    )

    refresh_clicked = False
    project_id = str(st.session_state.get("project_id")) if st.session_state.get("project_id") else None

    if show_project_selector and show_refresh_button:

        # Show refresh button only if a project exists
        if project_id:
            col_left, col_right = st.columns([3, 1])
            with col_left:
                project_id = render_project_selector(
                    selector_label,
                    show_create_button=show_create_button_when_empty,
                )            
            with col_right:
                st.write("")
                st.write("")
                refresh_clicked = st.button(
                    refresh_button_label,
                    use_container_width=True,
                    disabled=refresh_button_disabled
                )
        else:
            project_id = render_project_selector(
                selector_label,
                show_create_button=show_create_button_when_empty,
            ) 

    elif show_project_selector:
        project_id = render_project_selector(
            selector_label,
            show_create_button=show_create_button_when_empty,
        )

    elif show_refresh_button:
        refresh_clicked = st.button(
            refresh_button_label,
            use_container_width=True,
        )

    else:
        project_id = st.session_state.get("project_id")

    if metrics:
        render_metrics(metrics)

    return {
        "app": app,
        "user_id": user_id,
        "project_id": project_id,
        "refresh_clicked": refresh_clicked,
    }
