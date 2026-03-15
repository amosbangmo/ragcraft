import base64

import streamlit as st

from typing import cast
from src.app.ragcraft_app import RAGCraftApp
from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.ui.source_citations import render_source_citations
from src.auth.guards import require_authentication
from src.core.exceptions import (
    LLMServiceError,
    VectorStoreError,
    DocStoreError,
)


st.set_page_config(
    page_title="Chat | RAGCraft",
    page_icon="💬",
    layout="wide",
)

require_authentication("pages/chat.py")
apply_layout()


def _get_user_error_message(exc: Exception, default_message: str) -> str:
    return getattr(exc, "user_message", default_message)


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
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")
        start_element_index = metadata.get("start_element_index")
        end_element_index = metadata.get("end_element_index")

        title_parts = [f"[{i}] {source_file}"]

        if content_type == "table" and table_title:
            title_parts.append(f"— {table_title}")
        elif content_type == "image" and image_title:
            title_parts.append(f"— {image_title}")

        if page_number is not None:
            title_parts.append(f"— page {page_number}")
        elif page_start is not None and page_end is not None:
            if page_start == page_end:
                title_parts.append(f"— page {page_start}")
            else:
                title_parts.append(f"— pages {page_start}-{page_end}")

        if content_type == "text" and start_element_index is not None and end_element_index is not None:
            if start_element_index == end_element_index:
                title_parts.append(f"— element {start_element_index}")
            else:
                title_parts.append(f"— elements {start_element_index}-{end_element_index}")

        with st.expander(" ".join(title_parts)):
            if content_type == "text":
                st.write(raw_content)
                continue

            if content_type == "table":
                if table_title:
                    st.markdown(f"**{table_title}**")

                if raw_content:
                    _render_html_table(raw_content)
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

app = cast(RAGCraftApp, header["app"])
user_id = str(header["user_id"])
project_id = str(header["project_id"]) if header["project_id"] else None

if not project_id:
    st.stop()

if header["refresh_clicked"]:
    try:
        app.invalidate_project_chain(user_id, project_id)
        st.success("Project retrieval cache cleared.")
    except Exception as exc:
        st.error(_get_user_error_message(exc, "Unable to refresh the retrieval cache."))

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
    try:
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

        render_source_citations(getattr(response, "citations", []))
        render_raw_assets(response.raw_assets)

        app.chat_service.add_assistant_message(response.answer)

    except VectorStoreError as exc:
        st.error(_get_user_error_message(exc, "Unable to query the FAISS index for this question."))
    except DocStoreError as exc:
        st.error(_get_user_error_message(exc, "Unable to retrieve supporting assets from SQLite."))
    except LLMServiceError as exc:
        st.error(_get_user_error_message(exc, "The language model failed while generating the answer."))
    except Exception as exc:
        st.error(_get_user_error_message(exc, f"Unexpected error while answering the question: {exc}"))
