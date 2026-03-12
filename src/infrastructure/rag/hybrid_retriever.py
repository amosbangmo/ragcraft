from langchain_classic.retrievers import EnsembleRetriever
from langchain_classic.retrievers import BM25Retriever


def build_hybrid_retriever(vector_store, documents):

    vector_retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )

    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = 4

    hybrid_retriever = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=[0.7, 0.3]
    )

    return hybrid_retriever