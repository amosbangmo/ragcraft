from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

from src.core.config import LLM
from src.infrastructure.rag.prompts import get_rag_prompt
from src.infrastructure.rag.reranker import Reranker

reranker = Reranker()

def build_qa_chain(retriever):
    """
    Build the Retrieval-Augmented Generation (RAG) chain.

    This chain retrieves relevant documents using the retriever
    and then generates an answer using the LLM and the RAG prompt.

    Args:
        retriever: LangChain retriever object

    Returns:
        A LangChain retrieval chain
    """

    if retriever is None:
        return None

    # Get the prompt used for the RAG system
    prompt = get_rag_prompt()

    # Chain responsible for combining retrieved documents with the prompt
    combine_docs_chain = create_stuff_documents_chain(
        llm=LLM,
        prompt=prompt
    )

    # Full RAG pipeline
    qa_chain = create_retrieval_chain(
        retriever,
        combine_docs_chain
    )

    return qa_chain

def ask_question(chain, question: str, chat_history=None):
    """
    Execute a question against the RAG chain.

    The answer is generated first by the chain.
    Retrieved documents are then reranked for display purposes only.
    """

    if chain is None:
        return None

    if chat_history is None:
        chat_history = []

    try:
        result = chain.invoke({
            "input": question,
            "chat_history": chat_history
        })
    except Exception:
        return None

    if not result:
        return None

    docs = result.get("context", [])

    if docs:
        try:
            ranked_docs = reranker.rerank(question, docs)
            result["context"] = ranked_docs[:4]
        except Exception:
            result["context"] = docs[:4]
    else:
        result["context"] = []

    return result

# def ask_question(retriever, question: str):
#     """
#     Retrieve documents, rerank them, then generate the final answer
#     using the reranked context.
#     """

#     if retriever is None:
#         return None

#     try:
#         docs = retriever.invoke(question)
#     except Exception:
#         return None

#     if not docs:
#         return {
#             "answer": "I don't know based on the provided documents.",
#             "context": []
#         }

#     ranked_docs = reranker.rerank(question, docs)
#     top_docs = ranked_docs[:4]

#     context = "\n\n".join(doc.page_content for doc in top_docs)

#     prompt = get_rag_prompt().format(
#         context=context,
#         input=question
#     )

#     try:
#         response = LLM.invoke(prompt)
#     except Exception:
#         return None

#     answer = response.content if hasattr(response, "content") else str(response)

#     return {
#         "answer": answer,
#         "context": top_docs
#     }