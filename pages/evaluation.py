import streamlit as st

from src.rag.qa_chain import ask_question
from src.evaluation.confidence import compute_confidence

def render():

    st.title("RAG Evaluation")

    chain = st.session_state.get("chain")

    if chain is None:
        st.warning("No RAG chain loaded.")
        return

    question = st.text_input("Test question")

    if st.button("Run evaluation"):

        result = ask_question(chain, question)

        answer = result.get("answer")
        docs = result.get("context", [])

        confidence = compute_confidence(docs)

        st.markdown("### Answer")
        st.write(answer)

        st.markdown("### Confidence")
        st.write(confidence)

        st.markdown("### Retrieved Documents")

        for doc in docs:

            st.markdown(doc.page_content[:300])

render()
