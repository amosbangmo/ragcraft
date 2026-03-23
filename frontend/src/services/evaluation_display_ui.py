"""Small shared strings for evaluation UI (no backend imports)."""


def format_bool_toggle_on_off(value: bool) -> str:
    return "on" if value else "off"
