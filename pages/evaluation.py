import streamlit as st

from src.core.app_state import get_app
from src.core.session import get_user_id


st.title("RAG Evaluation")

app = get_app()

user_id = get_user_id()
project_id = st.session_state.get("project_id")

if not project_id:
    st.warning("Please select a project first.")
    st.stop()

question = st.text_input("Test question")

if st.button("Run evaluation") and question:

    response = app.ask_question(user_id, project_id, question)

    if response is None:
        st.warning("No RAG response available.")
        st.stop()

    st.markdown("### Answer")
    st.write(response.answer)

    st.markdown("### Confidence")
    st.write(response.confidence)

    st.markdown("### Retrieved Documents")

    for doc in response.source_documents:
        st.markdown(doc.page_content[:300])
