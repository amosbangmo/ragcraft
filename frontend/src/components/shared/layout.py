from components.shared.theme import apply_theme
from components.shared.navigation import render_navigation


def apply_layout(hide_sidebar=False):
    apply_theme()
    render_navigation(hide_sidebar)
