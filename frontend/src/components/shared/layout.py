from components.shared.navigation import render_navigation
from components.shared.theme import apply_theme


def apply_layout(hide_sidebar=False):
    apply_theme()
    render_navigation(hide_sidebar)
