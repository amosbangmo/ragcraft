import html
import streamlit as st


def get_initials(display_name: str | None) -> str:
    """
    Build initials from a display name.
    Example:
    - 'Amos Bangmo' -> 'AB'
    - 'Administrator' -> 'A'
    """
    if not display_name:
        return "?"

    parts = [part.strip() for part in display_name.split() if part.strip()]

    if not parts:
        return "?"

    if len(parts) == 1:
        return parts[0][:1].upper()

    return (parts[0][0] + parts[1][0]).upper()


def render_initials_avatar(display_name: str | None, size: int = 88):
    """
    Render a circular avatar with user initials.
    """
    initials = html.escape(get_initials(display_name))

    font_size = max(16, int(size * 0.32))

    st.markdown(
        f"""
        <div style="
            width: {size}px;
            height: {size}px;
            border-radius: 50%;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: {font_size}px;
            box-shadow: 0 6px 18px rgba(37,99,235,0.25);
            border: 2px solid rgba(255,255,255,0.15);
            margin-bottom: 8px;
        ">
            {initials}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_user_avatar(avatar_path: str | None, display_name: str | None, size: int = 88):
    """
    Render the uploaded avatar if available,
    otherwise render a default initials avatar.
    """
    if avatar_path:
        try:
            st.image(avatar_path, width=size)
            return
        except Exception:
            pass

    render_initials_avatar(display_name=display_name, size=size)
