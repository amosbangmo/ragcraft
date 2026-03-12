from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.services.vectorstore_service import VectorStoreService
from src.services.evaluation_service import EvaluationService
from src.infrastructure.rag.retriever import get_retriever
from src.infrastructure.rag.qa_chain import build_qa_chain, ask_question


class RAGService:
    def __init__(
        self,
        vectorstore_service: VectorStoreService,
        evaluation_service: EvaluationService,
    ):
        self.vectorstore_service = vectorstore_service
        self.evaluation_service = evaluation_service

    def build_chain(self, project: Project):
        vector_store = self.vectorstore_service.load(project)

        if vector_store is None:
            return None

        retriever = get_retriever(vector_store)

        if retriever is None:
            return None

        return build_qa_chain(retriever)

    def ask_with_chain(self, chain, question: str, chat_history=None) -> RAGResponse | None:

        if chain is None:
            return None

        result = ask_question(chain, question, chat_history)

        if result is None:
            return None

        docs = result.get("context", [])
        answer = result.get("answer", "")

        confidence = self.evaluation_service.compute_confidence(docs)

        return RAGResponse(
            question=question,
            answer=answer,
            source_documents=docs,
            confidence=confidence,
        )

    def ask(self, project: Project, question: str, chat_history=None) -> RAGResponse | None:
        """
        Fallback method if no chain cache is used.
        """
        chain = self.build_chain(project)
        return self.ask_with_chain(chain, question, chat_history)
