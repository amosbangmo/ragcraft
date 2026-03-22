"""Run the full gold QA benchmark for a project (``POST /evaluation/dataset/run`` and in-process clients)."""

from __future__ import annotations

from src.domain.benchmark_result import BenchmarkResult
from src.application.evaluation.dtos import (
    ListQaDatasetEntriesQuery,
    RunGoldQaDatasetEvaluationCommand,
)
from src.application.use_cases.chat.generate_answer_from_pipeline import GenerateAnswerFromPipelineUseCase
from src.application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
from src.application.use_cases.evaluation.rag_answer_for_eval import run_rag_inspect_and_answer_for_eval
from src.domain.ports.gold_qa_benchmark_port import GoldQaBenchmarkPort
from src.domain.ports.project_workspace_port import ProjectWorkspacePort

from .list_qa_dataset_entries import ListQaDatasetEntriesUseCase


class RunGoldQaDatasetEvaluationUseCase:
    def __init__(
        self,
        *,
        list_qa_dataset_entries: ListQaDatasetEntriesUseCase,
        project_service: ProjectWorkspacePort,
        inspect_pipeline: InspectRagPipelineUseCase,
        generate_answer_from_pipeline: GenerateAnswerFromPipelineUseCase,
        gold_benchmark: GoldQaBenchmarkPort,
    ) -> None:
        self._list_qa = list_qa_dataset_entries
        self._project_service = project_service
        self._inspect_pipeline = inspect_pipeline
        self._generate_answer_from_pipeline = generate_answer_from_pipeline
        self._gold_benchmark = gold_benchmark

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
                inspect_pipeline=self._inspect_pipeline,
                generate_answer_from_pipeline=self._generate_answer_from_pipeline,
                project=project,
                question=entry.question,
                enable_query_rewrite=command.enable_query_rewrite,
                enable_hybrid_retrieval=command.enable_hybrid_retrieval,
            )

        return self._gold_benchmark.evaluate_gold_qa_dataset(
            entries=entries,
            pipeline_runner=pipeline_runner,
        )
