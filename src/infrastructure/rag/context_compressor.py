from langchain_classic.retrievers.document_compressors import LLMChainExtractor
from src.core.config import LLM


def build_context_compressor(retriever):

    compressor = LLMChainExtractor.from_llm(LLM)

    compressed_retriever = compressor | retriever

    return compressed_retriever