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


def render_sources(docs):
    if not docs:
        return

    st.markdown("### Sources")

    for i, doc in enumerate(docs):
        file_name = doc.metadata.get("file_name", "unknown")
        chunk_id = doc.metadata.get("chunk_id", "?")
        preview = doc.page_content[:220]

        st.markdown(
            f"""
            <div class="source-card">
                <div class="source-title">[{i+1}] {file_name} — chunk {chunk_id}</div>
                <div class="source-preview">{preview}...</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_chat_history(messages, max_messages: int = 6):
    recent_messages = messages[-max_messages:]
    return [f"{msg['role']}: {msg['content']}" for msg in recent_messages]


header = render_page_header(
    badge="Chat",
    title="Talk to your documents",
    subtitle="Ask questions, inspect citations and refresh the project chain when needed.",
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
    st.success("Project chain cache cleared.")

project = app.get_project(user_id, project_id)
documents = app.list_project_documents(user_id, project_id)

st.columns(2)
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

    render_sources(response.source_documents)

    app.chat_service.add_assistant_message(response.answer)
