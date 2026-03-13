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


def render_raw_assets(raw_assets):
    if not raw_assets:
        return

    st.markdown("### Raw sources used")

    for i, asset in enumerate(raw_assets, start=1):
        source_file = asset.get("source_file", "unknown")
        content_type = asset.get("content_type", "unknown")
        raw_content = asset.get("raw_content", "")
        doc_id = asset.get("doc_id", "?")
        metadata = asset.get("metadata", {}) or {}

        with st.expander(f"[{i}] {source_file} — {content_type} — doc_id {doc_id}"):
            st.caption(f"Metadata: {metadata}")

            if content_type == "image":
                st.info("Image asset stored as base64 in SQLite. Raw payload hidden in UI for readability.")
            else:
                st.write(raw_content)


def build_chat_history(messages, max_messages: int = 6):
    recent_messages = messages[-max_messages:]
    return [f"{msg['role']}: {msg['content']}" for msg in recent_messages]


header = render_page_header(
    badge="Chat",
    title="Talk to your documents",
    subtitle="Ask questions, inspect raw evidence, and refresh the project retrieval state when needed.",
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
