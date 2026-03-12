from src.services.project_service import ProjectService
from src.services.ingestion_service import IngestionService
from src.services.vectorstore_service import VectorStoreService
from src.services.evaluation_service import EvaluationService
from src.services.chat_service import ChatService
from src.services.rag_service import RAGService

from src.core.chain_state import (
    get_cached_chain,
    set_cached_chain,
    invalidate_project_chain,
    invalidate_all_project_chains,
)


class RAGCraftApp:

    def __init__(self):

        self.project_service = ProjectService()
        self.ingestion_service = IngestionService()
        self.vectorstore_service = VectorStoreService()
        self.evaluation_service = EvaluationService()
        self.chat_service = ChatService()

        self._rag_service = None

    @property
    def rag_service(self):

        if self._rag_service is None:
            self._rag_service = RAGService(
                vectorstore_service=self.vectorstore_service,
                evaluation_service=self.evaluation_service,
            )

        return self._rag_service

    def get_project(self, user_id: str, project_id: str):
        return self.project_service.get_project(user_id, project_id)

    def create_project(self, user_id: str, project_id: str):
        return self.project_service.create_project(user_id, project_id)

    def list_projects(self, user_id: str):
        return self.project_service.list_projects(user_id)

    def get_or_build_project_chain(self, user_id: str, project_id: str):
        """
        Return a cached RAG chain for the given project,
        or build and cache it if missing.
        """

        project = self.get_project(user_id, project_id)
        project_id = project.project_id

        cached_chain = get_cached_chain(project_id)

        if cached_chain is not None:
            return cached_chain

        chain = self.rag_service.build_chain(project)

        if chain is not None:
            set_cached_chain(project_id, chain)

        return chain

    def invalidate_project_chain(self, user_id: str, project_id: str):
        project = self.get_project(user_id, project_id)
        invalidate_project_chain(project.project_id)

    def invalidate_all_project_chains(self):
        invalidate_all_project_chains()

    def ingest_uploaded_file(self, user_id: str, project_id: str, uploaded_file):

        project = self.get_project(user_id, project_id)

        chunks = self.ingestion_service.ingest_uploaded_file(
            project,
            uploaded_file
        )

        self.vectorstore_service.index_documents(project, chunks)

        # Important: the index changed, so the chain must be rebuilt
        self.invalidate_project_chain(user_id, project_id)

        return chunks

    def ask_question(self, user_id: str, project_id: str, question: str, chat_history=None):

        project = self.get_project(user_id, project_id)

        return self.rag_service.ask(project, question, chat_history)
