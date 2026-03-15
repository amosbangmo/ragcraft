import streamlit as st

from typing import cast
from src.app.ragcraft_app import RAGCraftApp
from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.ui.raw_assets import render_raw_assets
from src.ui.source_citations import render_source_citations
from src.auth.guards import require_authentication
from src.core.error_utils import get_user_error_message
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


def render_chat_history(messages):
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


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
        st.error(get_user_error_message(exc, "Unable to refresh the retrieval cache."))

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
        render_raw_assets(
            response.raw_assets,
            heading="### Sources utilisées",
            mode="chat",
        )

        app.chat_service.add_assistant_message(response.answer)

    except VectorStoreError as exc:
        st.error(get_user_error_message(exc, "Unable to query the FAISS index for this question."))
    except DocStoreError as exc:
        st.error(get_user_error_message(exc, "Unable to retrieve supporting assets from SQLite."))
    except LLMServiceError as exc:
        st.error(get_user_error_message(exc, "The language model failed while generating the answer."))
    except Exception as exc:
        st.error(get_user_error_message(exc, f"Unexpected error while answering the question: {exc}"))
