"""Run the full gold QA benchmark for a project (``POST /evaluation/dataset/run`` and in-process clients)."""

from __future__ import annotations

from src.domain.benchmark_result import BenchmarkResult
from src.application.evaluation.dtos import (
    ListQaDatasetEntriesQuery,
    RunGoldQaDatasetEvaluationCommand,
)
from src.application.use_cases.evaluation.rag_answer_for_eval import run_rag_inspect_and_answer_for_eval
from src.infrastructure.services.evaluation_service import EvaluationService
from src.infrastructure.services.project_service import ProjectService
from src.infrastructure.services.rag_service import RAGService

from .list_qa_dataset_entries import ListQaDatasetEntriesUseCase


class RunGoldQaDatasetEvaluationUseCase:
    def __init__(
        self,
        *,
        list_qa_dataset_entries: ListQaDatasetEntriesUseCase,
        project_service: ProjectService,
        rag_service: RAGService,
        evaluation_service: EvaluationService,
    ) -> None:
        self._list_qa = list_qa_dataset_entries
        self._project_service = project_service
        self._rag = rag_service
        self._evaluation = evaluation_service

    def execute(self, command: RunGoldQaDatasetEvaluationCommand) -> BenchmarkResult:
        entries = self._list_qa.execute(
            ListQaDatasetEntriesQuery(
                user_id=command.user_id,
                project_id=command.project_id,
            )
        )
        project = self._project_service.get_project(command.user_id, command.project_id)

        def pipeline_runner(entry):
            return run_rag_inspect_and_answer_for_eval(
                rag_service=self._rag,
                project=project,
                question=entry.question,
                enable_query_rewrite=command.enable_query_rewrite,
                enable_hybrid_retrieval=command.enable_hybrid_retrieval,
            )

        return self._evaluation.evaluate_gold_qa_dataset(
            entries=entries,
            pipeline_runner=pipeline_runner,
        )
