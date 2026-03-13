from src.ui.theme import apply_theme
from src.ui.navigation import render_navigation


def apply_layout(hide_sidebar=False):
    apply_theme()
    render_navigation(hide_sidebar)
