import streamlit as st


def render_source_citations(citations):
    if not citations:
        return

    st.markdown("### Citations")

    for citation in citations:
        display_label = citation.get("display_label", "Unknown source")
        inline_label = citation.get("inline_label")

        if inline_label:
            st.markdown(f"- **{inline_label}** — {display_label}")
        else:
            st.markdown(f"- {display_label}")
