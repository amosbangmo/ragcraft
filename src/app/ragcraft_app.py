from time import perf_counter

from src.infrastructure.persistence.db import init_app_db
from src.auth.auth_service import AuthService
from src.services.project_service import ProjectService
from src.services.ingestion_service import IngestionService
from src.services.vectorstore_service import VectorStoreService
from src.services.evaluation_service import EvaluationService
from src.services.chat_service import ChatService
from src.services.rag_service import RAGService
from src.services.docstore_service import DocStoreService
from src.services.reranking_service import RerankingService
from src.services.retrieval_comparison_service import RetrievalComparisonService
from src.services.qa_dataset_service import QADatasetService
from src.services.qa_dataset_generation_service import QADatasetGenerationService

from src.core.chain_state import (
    get_cached_chain,
    set_cached_chain,
    invalidate_project_chain,
    invalidate_all_project_chains,
)


class RAGCraftApp:
    def __init__(self):
        init_app_db()

        self.auth_service = AuthService()
        self.project_service = ProjectService()
        self.ingestion_service = IngestionService()
        self.vectorstore_service = VectorStoreService()
        self.evaluation_service = EvaluationService()
        self.chat_service = ChatService()
        self.docstore_service = DocStoreService()
        self.reranking_service = RerankingService()
        self.qa_dataset_service = QADatasetService()
        self.qa_dataset_generation_service = QADatasetGenerationService(
            docstore_service=self.docstore_service,
            project_service=self.project_service,
        )

        self._rag_service = None
        self._retrieval_comparison_service = None

    @property
    def rag_service(self):
        if self._rag_service is None:
            self._rag_service = RAGService(
                vectorstore_service=self.vectorstore_service,
                evaluation_service=self.evaluation_service,
                docstore_service=self.docstore_service,
                reranking_service=self.reranking_service,
            )

        return self._rag_service

    @property
    def retrieval_comparison_service(self):
        if self._retrieval_comparison_service is None:
            self._retrieval_comparison_service = RetrievalComparisonService(
                rag_service=self.rag_service,
            )
        return self._retrieval_comparison_service

    def get_current_user_record(self):
        return self.auth_service.get_current_user_record()

    def format_created_at(self, created_at: str | None) -> str:
        return self.auth_service.format_created_at(created_at)

    def update_profile(
        self,
        *,
        user_id: str,
        new_username: str,
        new_display_name: str,
    ) -> tuple[bool, str]:
        return self.auth_service.update_profile(
            user_id=user_id,
            new_username=new_username,
            new_display_name=new_display_name,
        )

    def change_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
        confirm_new_password: str,
    ) -> tuple[bool, str]:
        return self.auth_service.change_password(
            user_id=user_id,
            current_password=current_password,
            new_password=new_password,
            confirm_new_password=confirm_new_password,
        )

    def save_avatar(self, user_id: str, uploaded_file) -> tuple[bool, str]:
        return self.auth_service.save_avatar(user_id, uploaded_file)

    def remove_avatar(self, user_id: str) -> tuple[bool, str]:
        return self.auth_service.remove_avatar(user_id)

    def delete_account(self, *, user_id: str, current_password: str) -> tuple[bool, str]:
        return self.auth_service.delete_account(
            user_id=user_id,
            current_password=current_password,
        )

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

    def get_project_document_details(self, user_id: str, project_id: str) -> list[dict]:
        project = self.get_project(user_id, project_id)
        documents = self.list_project_documents(user_id, project_id)

        details = []

        for doc_name in documents:
            file_path = project.path / doc_name

            asset_count = self.docstore_service.count_assets_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=doc_name,
            )

            asset_stats = self.docstore_service.get_asset_stats_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=doc_name,
            )

            details.append(
                {
                    "name": doc_name,
                    "project_id": project_id,
                    "path": str(file_path),
                    "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
                    "asset_count": asset_count,
                    "text_count": int(asset_stats.get("text_count", 0)),
                    "table_count": int(asset_stats.get("table_count", 0)),
                    "image_count": int(asset_stats.get("image_count", 0)),
                    "latest_ingested_at": asset_stats.get("latest_ingested_at"),
                }
            )

        return details

    def get_document_assets(self, user_id: str, project_id: str, source_file: str) -> list[dict]:
        return self.docstore_service.list_assets_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
        )

    def get_or_build_project_chain(self, user_id: str, project_id: str):
        project = self.get_project(user_id, project_id)
        project_key = project.project_id

        cached_object = get_cached_chain(project_key)

        if cached_object is not None:
            return cached_object

        cached_object = self.rag_service.build_chain(project)

        if cached_object is not None:
            set_cached_chain(project_key, cached_object)

        return cached_object

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

    def delete_project_document(self, user_id: str, project_id: str, source_file: str) -> dict:
        project = self.get_project(user_id, project_id)
        file_path = project.path / source_file

        existing_doc_ids = self.docstore_service.get_doc_ids_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
        )

        deleted_vectors = 0
        deleted_assets = 0
        file_deleted = False

        if existing_doc_ids:
            self.vectorstore_service.delete_documents(project, existing_doc_ids)
            deleted_vectors = len(existing_doc_ids)

            deleted_assets = self.docstore_service.delete_assets_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=source_file,
            )

        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            file_deleted = True

        self.invalidate_project_chain(user_id, project_id)

        return {
            "source_file": source_file,
            "file_deleted": file_deleted,
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

        self.invalidate_project_chain(user_id, project_id)

        return {
            "raw_assets": raw_assets,
            "replacement_info": replacement_info,
        }

    def reindex_project_document(self, user_id: str, project_id: str, source_file: str):
        project = self.get_project(user_id, project_id)
        file_path = project.path / source_file

        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Document not found on disk: {source_file}")

        replacement_info = self.replace_document_assets(
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
        )

        summary_documents, raw_assets = self.ingestion_service.ingest_file_path(
            project=project,
            file_path=file_path,
            source_file=source_file,
        )

        if not raw_assets:
            raise ValueError(f"No raw assets generated for file: {source_file}")

        for asset in raw_assets:
            self.docstore_service.save_asset(**asset)

        if summary_documents:
            self.vectorstore_service.index_documents(project, summary_documents)

        self.invalidate_project_chain(user_id, project_id)

        return {
            "raw_assets": raw_assets,
            "replacement_info": replacement_info,
        }

    def ask_question(self, user_id: str, project_id: str, question: str, chat_history=None):
        project = self.get_project(user_id, project_id)
        return self.rag_service.ask(project, question, chat_history)

    def inspect_retrieval(
        self,
        user_id: str,
        project_id: str,
        question: str,
        chat_history=None,
        *,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ):
        project = self.get_project(user_id, project_id)
        return self.rag_service.inspect_pipeline(
            project,
            question,
            chat_history,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

    def compare_retrieval_modes(
        self,
        *,
        user_id: str,
        project_id: str,
        questions: list[str],
        enable_query_rewrite: bool,
    ) -> dict:
        project = self.get_project(user_id, project_id)
        return self.retrieval_comparison_service.compare(
            project=project,
            questions=questions,
            enable_query_rewrite=enable_query_rewrite,
        )

    def create_qa_dataset_entry(
        self,
        *,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ):
        return self.qa_dataset_service.create_entry(
            user_id=user_id,
            project_id=project_id,
            question=question,
            expected_answer=expected_answer,
            expected_doc_ids=expected_doc_ids,
            expected_sources=expected_sources,
        )

    def list_qa_dataset_entries(
        self,
        *,
        user_id: str,
        project_id: str,
    ):
        return self.qa_dataset_service.list_entries(
            user_id=user_id,
            project_id=project_id,
        )

    def update_qa_dataset_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ):
        return self.qa_dataset_service.update_entry(
            entry_id=entry_id,
            user_id=user_id,
            project_id=project_id,
            question=question,
            expected_answer=expected_answer,
            expected_doc_ids=expected_doc_ids,
            expected_sources=expected_sources,
        )

    def delete_qa_dataset_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
    ) -> bool:
        return self.qa_dataset_service.delete_entry(
            entry_id=entry_id,
            user_id=user_id,
            project_id=project_id,
        )

    def generate_qa_dataset_entries(
        self,
        *,
        user_id: str,
        project_id: str,
        num_questions: int,
        source_files: list[str] | None = None,
        generation_mode: str = "append",
    ) -> dict:
        normalized_mode = (generation_mode or "append").strip().lower()
        if normalized_mode not in {"append", "replace", "append_dedup"}:
            raise ValueError("generation_mode must be one of: append, replace, append_dedup.")

        deleted_existing_entries = 0

        if normalized_mode == "replace":
            deleted_existing_entries = self.qa_dataset_service.delete_all_entries(
                user_id=user_id,
                project_id=project_id,
            )

        existing_question_keys = set()
        if normalized_mode == "append_dedup":
            existing_question_keys = self.qa_dataset_service.existing_question_keys(
                user_id=user_id,
                project_id=project_id,
            )

        generated_entries = self.qa_dataset_generation_service.generate_entries(
            user_id=user_id,
            project_id=project_id,
            num_questions=num_questions,
            source_files=source_files,
        )

        created_entries = []
        skipped_duplicates = []

        for item in generated_entries:
            question = item["question"]
            question_key = self.qa_dataset_service.normalized_question_key(question)

            if normalized_mode == "append_dedup" and question_key in existing_question_keys:
                skipped_duplicates.append(question)
                continue

            created_entry = self.create_qa_dataset_entry(
                user_id=user_id,
                project_id=project_id,
                question=question,
                expected_answer=item.get("expected_answer"),
                expected_doc_ids=item.get("expected_doc_ids", []),
                expected_sources=item.get("expected_sources", []),
            )
            created_entries.append(created_entry)

            if normalized_mode == "append_dedup":
                existing_question_keys.add(question_key)

        return {
            "generation_mode": normalized_mode,
            "deleted_existing_entries": deleted_existing_entries,
            "created_entries": created_entries,
            "skipped_duplicates": skipped_duplicates,
            "requested_questions": int(num_questions),
            "raw_generated_count": len(generated_entries),
        }

    def evaluate_gold_qa_dataset(
        self,
        *,
        user_id: str,
        project_id: str,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
    ) -> dict:
        entries = self.list_qa_dataset_entries(
            user_id=user_id,
            project_id=project_id,
        )
        project = self.get_project(user_id, project_id)

        def pipeline_runner(entry):
            started = perf_counter()
            pipeline = self.inspect_retrieval(
                user_id=user_id,
                project_id=project_id,
                question=entry.question,
                chat_history=[],
                enable_query_rewrite_override=enable_query_rewrite,
                enable_hybrid_retrieval_override=enable_hybrid_retrieval,
            )

            answer = None
            if pipeline is not None:
                answer = self.rag_service.answer_from_pipeline(project, pipeline)

            latency_ms = (perf_counter() - started) * 1000.0
            return {
                "pipeline": pipeline,
                "answer": answer,
                "latency_ms": latency_ms,
            }

        return self.evaluation_service.evaluate_gold_qa_dataset(
            entries=entries,
            pipeline_runner=pipeline_runner,
        )
