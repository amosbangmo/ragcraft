from datetime import datetime

from src.infrastructure.persistence.db import init_app_db
from src.application.evaluation.use_cases.create_qa_dataset_entry import CreateQaDatasetEntryUseCase
from src.application.evaluation.use_cases.delete_qa_dataset_entry import DeleteQaDatasetEntryUseCase
from src.application.evaluation.dtos import GenerateQaDatasetCommand
from src.application.evaluation.use_cases.generate_qa_dataset import GenerateQaDatasetUseCase
from src.application.evaluation.use_cases.list_qa_dataset_entries import ListQaDatasetEntriesUseCase
from src.application.evaluation.use_cases.run_gold_qa_dataset_evaluation import (
    RunGoldQaDatasetEvaluationUseCase,
)
from src.application.evaluation.use_cases.run_manual_evaluation import RunManualEvaluationUseCase
from src.application.evaluation.use_cases.update_qa_dataset_entry import UpdateQaDatasetEntryUseCase
from src.application.ingestion.use_cases.delete_document import DeleteDocumentUseCase
from src.application.ingestion.dtos import DeleteDocumentCommand, ReindexDocumentCommand
from src.application.ingestion.use_cases.ingest_uploaded_file import IngestUploadedFileUseCase
from src.application.ingestion.use_cases.replace_document_assets import (
    replace_document_assets_for_reingest,
)
from src.application.ingestion.use_cases.reindex_document import ReindexDocumentUseCase
from src.auth.auth_service import AuthService
from src.services.project_service import ProjectService
from src.services.ingestion_service import IngestionService
from src.services.vectorstore_service import VectorStoreService
from src.services.evaluation_service import EvaluationService
from src.services.llm_judge_service import LLMJudgeService
from src.services.chat_service import ChatService
from src.services.query_log_service import QueryLogService
from src.services.project_settings_service import ProjectSettingsService
from src.services.rag_service import RAGService
from src.services.retrieval_settings_service import RetrievalSettingsService
from src.services.docstore_service import DocStoreService
from src.services.reranking_service import RerankingService
from src.services.retrieval_comparison_service import RetrievalComparisonService
from src.services.qa_dataset_service import QADatasetService
from src.services.qa_dataset_generation_service import QADatasetGenerationService
from src.application.evaluation.benchmark_export_dtos import (
    BenchmarkExportArtifacts,
    BuildBenchmarkExportCommand,
)
from src.application.evaluation.use_cases.build_benchmark_export_artifacts import (
    BuildBenchmarkExportArtifactsUseCase,
)
from src.domain.benchmark_result import BenchmarkResult
from src.domain.retrieval_filters import RetrievalFilters
from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.domain.pipeline_payloads import PipelineBuildResult

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
        self.evaluation_service = EvaluationService(llm_judge_service=LLMJudgeService())
        self.chat_service = ChatService()
        self.docstore_service = DocStoreService()
        self.reranking_service = RerankingService()
        self.qa_dataset_service = QADatasetService()
        self.qa_dataset_generation_service = QADatasetGenerationService(
            docstore_service=self.docstore_service,
            project_service=self.project_service,
        )
        self.project_settings_service = ProjectSettingsService()

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
                query_log_service=QueryLogService(),
                retrieval_settings_service=RetrievalSettingsService(
                    project_settings_service=self.project_settings_service,
                ),
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
        return replace_document_assets_for_reingest(
            project=project,
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
            docstore_service=self.docstore_service,
            vectorstore_service=self.vectorstore_service,
            invalidate_project_chain=self.invalidate_project_chain,
        )

    def delete_project_document(self, user_id: str, project_id: str, source_file: str) -> dict:
        project = self.get_project(user_id, project_id)
        uc = DeleteDocumentUseCase(
            docstore_service=self.docstore_service,
            vectorstore_service=self.vectorstore_service,
            invalidate_project_chain=self.invalidate_project_chain,
        )
        return uc.execute(
            DeleteDocumentCommand(project=project, source_file=source_file)
        ).as_payload()

    def ingest_uploaded_file(self, user_id: str, project_id: str, uploaded_file):
        project = self.get_project(user_id, project_id)
        uc = IngestUploadedFileUseCase(
            ingestion_service=self.ingestion_service,
            docstore_service=self.docstore_service,
            vectorstore_service=self.vectorstore_service,
            invalidate_project_chain=self.invalidate_project_chain,
        )
        return uc.execute(project, uploaded_file).as_payload()

    def reindex_project_document(self, user_id: str, project_id: str, source_file: str):
        project = self.get_project(user_id, project_id)
        uc = ReindexDocumentUseCase(
            ingestion_service=self.ingestion_service,
            docstore_service=self.docstore_service,
            vectorstore_service=self.vectorstore_service,
            invalidate_project_chain=self.invalidate_project_chain,
        )
        return uc.execute(
            ReindexDocumentCommand(project=project, source_file=source_file)
        ).as_payload()

    def ask_question(
        self,
        user_id: str,
        project_id: str,
        question: str,
        chat_history=None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ):
        project = self.get_project(user_id, project_id)
        return self.rag_service.ask(
            project,
            question,
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

    def evaluate_manual_question(
        self,
        *,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ) -> ManualEvaluationResult:
        return RunManualEvaluationUseCase(
            project_service=self.project_service,
            rag_service=self.rag_service,
            evaluation_service=self.evaluation_service,
        ).execute(
            user_id=user_id,
            project_id=project_id,
            question=question,
            expected_answer=expected_answer,
            expected_doc_ids=expected_doc_ids,
            expected_sources=expected_sources,
        )

    def inspect_retrieval(
        self,
        user_id: str,
        project_id: str,
        question: str,
        chat_history=None,
        *,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict | None = None,
    ) -> PipelineBuildResult | None:
        project = self.get_project(user_id, project_id)
        return self.rag_service.inspect_pipeline(
            project,
            question,
            chat_history,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
            filters=filters,
            retrieval_settings=retrieval_settings,
        )

    def search_project_summaries(
        self,
        user_id: str,
        project_id: str,
        query: str,
        chat_history=None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ):
        project = self.get_project(user_id, project_id)
        return self.rag_service.preview_summary_recall(
            project,
            query,
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
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
        return CreateQaDatasetEntryUseCase(qa_dataset_service=self.qa_dataset_service).execute(
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
        return ListQaDatasetEntriesUseCase(qa_dataset_service=self.qa_dataset_service).execute(
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
        return UpdateQaDatasetEntryUseCase(qa_dataset_service=self.qa_dataset_service).execute(
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
        return DeleteQaDatasetEntryUseCase(qa_dataset_service=self.qa_dataset_service).execute(
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
        return GenerateQaDatasetUseCase(
            qa_dataset_service=self.qa_dataset_service,
            qa_dataset_generation_service=self.qa_dataset_generation_service,
        ).execute(
            GenerateQaDatasetCommand(
                user_id=user_id,
                project_id=project_id,
                num_questions=num_questions,
                source_files=source_files,
                generation_mode=generation_mode,
            )
        )

    def evaluate_gold_qa_dataset(
        self,
        *,
        user_id: str,
        project_id: str,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
    ):
        return RunGoldQaDatasetEvaluationUseCase(
            list_qa_dataset_entries=ListQaDatasetEntriesUseCase(
                qa_dataset_service=self.qa_dataset_service,
            ),
            project_service=self.project_service,
            rag_service=self.rag_service,
            evaluation_service=self.evaluation_service,
        ).execute(
            user_id=user_id,
            project_id=project_id,
            enable_query_rewrite=enable_query_rewrite,
            enable_hybrid_retrieval=enable_hybrid_retrieval,
        )

    def build_benchmark_export_artifacts(
        self,
        *,
        project_id: str,
        result: BenchmarkResult,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
        generated_at: datetime | None = None,
    ) -> BenchmarkExportArtifacts:
        """Build JSON/CSV/Markdown downloads; ``BenchmarkExportArtifacts.run_id`` mirrors ``result.run_id`` when set."""
        return BuildBenchmarkExportArtifactsUseCase().execute(
            BuildBenchmarkExportCommand(
                project_id=project_id,
                result=result,
                enable_query_rewrite=enable_query_rewrite,
                enable_hybrid_retrieval=enable_hybrid_retrieval,
                generated_at=generated_at,
            )
        )
