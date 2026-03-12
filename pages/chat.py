import streamlit as st

from src.vectorstore.faiss_store import get_project_vector_store
from src.rag.retriever import get_retriever
from src.rag.qa_chain import build_qa_chain
from src.rag.qa_chain import ask_question

def init_session():

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "chain" not in st.session_state:
        st.session_state.chain = None

def load_chain():

    user_id = st.session_state.get("user_id")
    project_id = st.session_state.get("project_id")

    if not user_id or not project_id:
        st.warning("Select a project first.")
        return None

    try:

        vector_store = get_project_vector_store(user_id, project_id)

        if vector_store is None:
            st.warning("No FAISS index found for this project.")
            return None

        retriever = get_retriever(vector_store, project_id)

        chain = build_qa_chain(retriever)

        return chain

    except Exception as e:

        st.error("Error loading FAISS index.")
        st.exception(e)

        return None 

def render_chat_history():

    for msg in st.session_state.messages:

        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def render_sources(docs):

    if not docs:
        return

    st.markdown("#### Sources")

    for i, doc in enumerate(docs):

        file_name = doc.metadata.get("file_name", "unknown")
        chunk_id = doc.metadata.get("chunk_id", "?")

        text = doc.page_content[:200]

        st.markdown(
            f"""
**[{i+1}] {file_name} — chunk {chunk_id}**

> {text}...
"""
        )


def stream_answer(chain, question):

    placeholder = st.empty()
    full_answer = ""

    try:

        for chunk in chain.stream({"input": question}):

            if "answer" in chunk:

                token = chunk["answer"]

                full_answer += token

                placeholder.markdown(full_answer + "▌")

        placeholder.markdown(full_answer)

    except Exception as e:

        st.error("Streaming error.")
        st.exception(e)

        return None, None

    result = ask_question(chain, question)

    docs = result.get("context", [])

    return full_answer, docs

def handle_chat():

    chain = st.session_state.chain

    if chain is None:
        st.info("No documents indexed yet.")
        return

    question = st.chat_input("Ask a question about your documents")

    if question:

        st.session_state.messages.append(
            {"role": "user", "content": question}
        )

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):

            answer, docs = stream_answer(chain, question)

            if answer:

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )

                render_sources(docs)
                
def render():

    st.title("💬 RAG Chat")

    init_session()

    if st.session_state.chain is None:
        st.session_state.chain = load_chain()

    render_chat_history()

    handle_chat()

render()
