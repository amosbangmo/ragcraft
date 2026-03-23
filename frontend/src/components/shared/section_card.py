from contextlib import contextmanager

import streamlit as st


def inject_section_card_styles() -> None:
    st.markdown(
        """
        <style>
        .rc-section-card {
            height: 100%;
            min-height: 300px;
            display: flex;
            flex-direction: column;
        }

        .rc-section-card--danger {
            border: 1px solid rgba(220, 38, 38, 0.25);
            box-shadow: 0 0 0 1px rgba(220, 38, 38, 0.06) inset;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def section_card(
    title: str,
    subtitle: str,
    min_height: int = 300,
    danger: bool = False,
):
    danger_class = " rc-section-card--danger" if danger else ""

    st.markdown(
        f"""
        <div class="section-card rc-section-card{danger_class}" style="min-height: {min_height}px;">
            <div class="card-title">{title}</div>
            <div class="card-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )

    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)
