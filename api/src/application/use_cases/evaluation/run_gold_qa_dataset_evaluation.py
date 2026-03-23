"""Run the full gold QA benchmark for a project (``POST /evaluation/dataset/run`` and in-process clients)."""

from __future__ import annotations

from application.dto.evaluation import (
    ListQaDatasetEntriesQuery,
    RunGoldQaDatasetEvaluationCommand,
)
from application.dto.rag.evaluation_pipeline import RagEvaluationPipelineInput
from application.orchestration.evaluation.rag_pipeline_orchestration import (
    execute_rag_inspect_then_answer_for_evaluation,
)
from application.use_cases.chat.pipeline_use_case_ports import (
    GenerateAnswerFromPipelinePort,
    InspectRagPipelinePort,
)
from domain.common.ports.gold_qa_benchmark_port import GoldQaBenchmarkPort
from domain.common.ports.project_workspace_port import ProjectWorkspacePort
from domain.evaluation.benchmark_result import BenchmarkResult
from domain.rag.rag_inspect_answer_run import RagInspectAnswerRun

from .list_qa_dataset_entries import ListQaDatasetEntriesUseCase


class RunGoldQaDatasetEvaluationUseCase:
    def __init__(
        self,
        *,
        list_qa_dataset_entries: ListQaDatasetEntriesUseCase,
        project_service: ProjectWorkspacePort,
        inspect_pipeline: InspectRagPipelinePort,
        generate_answer_from_pipeline: GenerateAnswerFromPipelinePort,
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

        def pipeline_runner(entry) -> RagInspectAnswerRun:
            return execute_rag_inspect_then_answer_for_evaluation(
                inspect_pipeline=self._inspect_pipeline,
                generate_answer_from_pipeline=self._generate_answer_from_pipeline,
                params=RagEvaluationPipelineInput(
                    project=project,
                    question=entry.question,
                    enable_query_rewrite=command.enable_query_rewrite,
                    enable_hybrid_retrieval=command.enable_hybrid_retrieval,
                ),
            )

        return self._gold_benchmark.evaluate_gold_qa_dataset(
            entries=entries,
            pipeline_runner=pipeline_runner,
        )
