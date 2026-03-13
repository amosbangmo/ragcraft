from src.auth.db import init_auth_db
from src.services.project_service import ProjectService
from src.services.ingestion_service import IngestionService
from src.services.vectorstore_service import VectorStoreService
from src.services.evaluation_service import EvaluationService
from src.services.chat_service import ChatService
from src.services.rag_service import RAGService
from src.services.docstore_service import DocStoreService

from src.core.chain_state import (
    get_cached_chain,
    set_cached_chain,
    invalidate_project_chain,
    invalidate_all_project_chains,
)


class RAGCraftApp:
    def __init__(self):
        init_auth_db()

        self.project_service = ProjectService()
        self.ingestion_service = IngestionService()
        self.vectorstore_service = VectorStoreService()
        self.evaluation_service = EvaluationService()
        self.chat_service = ChatService()
        self.docstore_service = DocStoreService()

        self._rag_service = None

    @property
    def rag_service(self):
        if self._rag_service is None:
            self._rag_service = RAGService(
                vectorstore_service=self.vectorstore_service,
                evaluation_service=self.evaluation_service,
                docstore_service=self.docstore_service,
            )

        return self._rag_service

    def get_project(self, user_id: str, project_id: str):
        return self.project_service.get_project(user_id, project_id)

    def create_project(self, user_id: str, project_id: str):
        return self.project_service.create_project(user_id, project_id)

    def list_projects(self, user_id: str):
        return self.project_service.list_projects(user_id)

    def list_project_documents(self, user_id: str, project_id: str) -> list[str]:
        project = self.get_project(user_id, project_id)

        if not project.path.exists():
            return []

        ignored_names = {"faiss_index", "logs.json"}

        documents = [
            item.name
            for item in project.path.iterdir()
            if item.is_file() and item.name not in ignored_names
        ]

        return sorted(documents)

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

    def replace_document_assets(self, user_id: str, project_id: str, source_file: str) -> dict:
        project = self.get_project(user_id, project_id)

        existing_doc_ids = self.docstore_service.get_doc_ids_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
        )

        deleted_vectors = 0
        deleted_assets = 0

        if existing_doc_ids:
            self.vectorstore_service.delete_documents(project, existing_doc_ids)
            deleted_vectors = len(existing_doc_ids)

            deleted_assets = self.docstore_service.delete_assets_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=source_file,
            )

            self.invalidate_project_chain(user_id, project_id)

        return {
            "existing_doc_ids": existing_doc_ids,
            "deleted_vectors": deleted_vectors,
            "deleted_assets": deleted_assets,
        }

    def ingest_uploaded_file(self, user_id: str, project_id: str, uploaded_file):
        project = self.get_project(user_id, project_id)

        replacement_info = self.replace_document_assets(
            user_id=user_id,
            project_id=project_id,
            source_file=uploaded_file.name,
        )

        summary_documents, raw_assets = self.ingestion_service.ingest_uploaded_file(
            project,
            uploaded_file,
        )

        if not raw_assets:
            raise ValueError(f"No raw assets generated for file: {uploaded_file.name}")

        for asset in raw_assets:
            self.docstore_service.save_asset(**asset)

        if summary_documents:
            self.vectorstore_service.index_documents(project, summary_documents)

        # Important: the index changed, so the chain must be rebuilt
        self.invalidate_project_chain(user_id, project_id)

        return {
            "raw_assets": raw_assets,
            "replacement_info": replacement_info,
        }

    def ask_question(self, user_id: str, project_id: str, question: str, chat_history=None):
        project = self.get_project(user_id, project_id)
        return self.rag_service.ask(project, question, chat_history)
