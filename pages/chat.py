import base64
import json

import streamlit as st

from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.auth.guards import require_authentication


require_authentication("pages/chat.py")
apply_layout()


def render_chat_history(messages):
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def _render_html_table(table_html: str):
    st.markdown(table_html, unsafe_allow_html=True)


def _render_base64_image(base64_content: str, title: str | None = None):
    try:
        image_bytes = base64.b64decode(base64_content)
        if title:
            st.markdown(f"**{title}**")
        st.image(image_bytes)
    except Exception:
        st.warning("Unable to render image asset.")


def _parse_table_raw_content(raw_content: str) -> dict:
    try:
        payload = json.loads(raw_content)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass

    return {
        "title": None,
        "html": None,
        "text": raw_content,
    }


def render_raw_assets(raw_assets):
    if not raw_assets:
        return

    st.markdown("### Sources utilisées")

    for i, asset in enumerate(raw_assets, start=1):
        source_file = asset.get("source_file", "unknown")
        content_type = asset.get("content_type", "unknown")
        raw_content = asset.get("raw_content", "")
        metadata = asset.get("metadata", {}) or {}

        table_title = metadata.get("table_title")
        image_title = metadata.get("image_title")
        page_number = metadata.get("page_number")

        title_parts = [f"[{i}] {source_file}"]

        if content_type == "table" and table_title:
            title_parts.append(f"— {table_title}")
        elif content_type == "image" and image_title:
            title_parts.append(f"— {image_title}")
        elif page_number:
            title_parts.append(f"— page {page_number}")

        with st.expander(" ".join(title_parts)):
            if content_type == "text":
                st.write(raw_content)
                continue

            if content_type == "table":
                table_payload = _parse_table_raw_content(raw_content)
                parsed_table_title = table_payload.get("title")
                table_html = table_payload.get("html")
                table_text = table_payload.get("text")

                if parsed_table_title:
                    st.markdown(f"**{parsed_table_title}**")

                if table_html:
                    _render_html_table(table_html)
                elif table_text:
                    st.write(table_text)
                else:
                    st.caption("Empty table payload.")
                continue

            if content_type == "image":
                _render_base64_image(raw_content, title=image_title)
                continue

            st.write(raw_content)


def build_chat_history(messages, max_messages: int = 6):
    recent_messages = messages[-max_messages:]
    return [f"{msg['role']}: {msg['content']}" for msg in recent_messages]


header = render_page_header(
    badge="Chat",
    title="Talk to your documents",
    subtitle="Ask questions and inspect the original raw evidence used by the system.",
    selector_label="Project for chat",
    show_project_selector=True,
    show_refresh_button=True,
)

app = header["app"]
user_id = header["user_id"]
project_id = header["project_id"]

if not project_id:
    st.stop()

if header["refresh_clicked"]:
    app.invalidate_project_chain(user_id, project_id)
    st.success("Project retrieval cache cleared.")

project = app.get_project(user_id, project_id)
documents = app.list_project_documents(user_id, project_id)

col1, col2 = st.columns(2)
with col1:
    st.metric("Current project", project.project_id)
with col2:
    st.metric("Documents", len(documents))

app.chat_service.init(project.project_id)

messages = app.chat_service.get_messages()
render_chat_history(messages)

question = st.chat_input("Ask a question about your documents")

if not question:
    st.stop()

app.chat_service.add_user_message(question)

with st.chat_message("user"):
    st.markdown(question)

with st.chat_message("assistant"):
    with st.spinner("Thinking..."):
        messages = app.chat_service.get_messages()
        chat_history = build_chat_history(messages)

        response = app.ask_question(
            user_id=user_id,
            project_id=project_id,
            question=question,
            chat_history=chat_history,
        )

    if response is None:
        st.warning("No answer available.")
        st.stop()

    st.markdown(response.answer)
    st.markdown(f"**Confidence:** {response.confidence}")

    render_raw_assets(response.raw_assets)

    app.chat_service.add_assistant_message(response.answer)
