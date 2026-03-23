import streamlit as st


def render_prompt_sources(prompt_sources):
    if not prompt_sources:
        return

    st.markdown("### Prompt sources")

    for src in prompt_sources:
        display_label = src.get("display_label", "Unknown source")
        inline_label = src.get("inline_label")

        if inline_label:
            st.markdown(f"- **{inline_label}** — {display_label}")
        else:
            st.markdown(f"- {display_label}")
