import html

import streamlit as st


def get_initials(display_name: str | None) -> str:
    if not display_name:
        return "?"

    parts = [p.strip() for p in display_name.split() if p.strip()]

    if len(parts) == 1:
        return parts[0][0].upper()

    return (parts[0][0] + parts[1][0]).upper()


def render_initials_avatar(display_name: str | None, size: int = 64):
    initials = html.escape(get_initials(display_name))

    font_size = max(14, int(size * 0.35))

    st.markdown(
        f"""
        <div style="
            display:flex;
            justify-content:center;
            margin-bottom:10px;
        ">
            <div style="
                width:{size}px;
                height:{size}px;
                border-radius:50%;
                background:linear-gradient(135deg,#2563eb,#1d4ed8);
                display:flex;
                align-items:center;
                justify-content:center;
                color:white;
                font-weight:700;
                font-size:{font_size}px;
                box-shadow:0 6px 18px rgba(37,99,235,0.25);
            ">
                {initials}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_user_avatar(avatar_path: str | None, display_name: str | None, size: int = 64):
    if avatar_path:
        try:
            st.markdown(
                '<div style="display:flex;justify-content:center;">', unsafe_allow_html=True
            )
            st.image(avatar_path, width=size)
            st.markdown("</div>", unsafe_allow_html=True)
            return
        except Exception:
            pass

    render_initials_avatar(display_name, size=size)
