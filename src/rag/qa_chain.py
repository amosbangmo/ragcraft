from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

from src.core.config import LLM
from src.rag.prompts import get_rag_prompt
from src.rag.reranker import Reranker

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


def ask_question(chain, question: str):
    """
    Execute a question against the RAG chain.

    Args:
        chain: retrieval chain
        question: user question

    Returns:
        dict containing:
        - answer
        - context (retrieved documents)
    """

    if chain is None:
        return None

    result = chain.invoke({"input": question})
    
    docs = result.get("context", [])

    # rerank documents
    ranked_docs = reranker.rerank(question, docs)

    result["context"] = ranked_docs[:4]
    
    return result