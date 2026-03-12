import streamlit as st

from src.core.app_state import get_app
from src.core.session import get_user_id
from src.ui.project_selector import render_project_selector
from src.ui.layout import apply_layout

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


st.markdown(
    """
    <div class="hero-card">
        <div class="hero-badge">Chat</div>
        <h1 class="hero-title">Talk to your documents</h1>
        <p class="hero-subtitle">
            Ask questions, inspect citations and refresh the project chain when needed.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

app = get_app()
user_id = get_user_id()

col_top_1, col_top_2 = st.columns([3, 1])
with col_top_1:
    project_id = render_project_selector("Project for chat")
with col_top_2:
    st.write("")
    st.write("")
    refresh_clicked = st.button("🔄 Refresh chain", use_container_width=True)

if not project_id:
    st.stop()

if refresh_clicked:
    app.invalidate_project_chain(user_id, project_id)
    st.success("Project chain cache cleared.")

project = app.get_project(user_id, project_id)
documents = app.list_project_documents(user_id, project_id)

m1, m2 = st.columns(2)
with m1:
    st.metric("Current project", project.project_id)
with m2:
    st.metric("Documents", len(documents))

app.chat_service.init(project.key)

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
