import streamlit as st

from src.core.app_state import get_app
from src.core.session import get_user_id


def render_chat_history(messages):
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def render_sources(docs):
    if not docs:
        return

    st.markdown("### Sources")

    for i, doc in enumerate(docs):
        file_name = doc.metadata.get("file_name", "unknown")
        chunk_id = doc.metadata.get("chunk_id", "?")
        preview = doc.page_content[:200]

        st.markdown(
            f"""
**[{i+1}] {file_name} — chunk {chunk_id}**

> {preview}...
"""
        )


def build_chat_history(messages, max_messages: int = 6):
    """
    Convert chat messages into a compact text-based history
    for the prompt. Only the most recent messages are kept
    to control token usage.
    """
    recent_messages = messages[-max_messages:]

    return [
        f"{msg['role']}: {msg['content']}"
        for msg in recent_messages
    ]


st.title("💬 RAG Chat")

app = get_app()

user_id = get_user_id()
project_id = st.session_state.get("project_id")

if not project_id:
    st.warning("Please select a project first.")
    st.stop()

project = app.get_project(user_id, project_id)

app.chat_service.init(project.project_id)

col1, col2 = st.columns([4, 1])

with col1:
    st.caption(f"Current project: **{project.project_id}**")

with col2:
    if st.button("🔄 Refresh chain"):
        app.invalidate_project_chain(user_id, project_id)
        st.success("Project chain cache cleared.")

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

    render_sources(response.source_documents)

    app.chat_service.add_assistant_message(response.answer)
