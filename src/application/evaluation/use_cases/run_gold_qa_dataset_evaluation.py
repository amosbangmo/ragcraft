"""Run the full gold QA benchmark for a project (``POST /evaluation/dataset/run`` and in-process clients)."""

from __future__ import annotations

from time import perf_counter

from src.domain.benchmark_result import BenchmarkResult
from src.domain.pipeline_latency import merge_with_answer_stage
from src.application.evaluation.dtos import (
    ListQaDatasetEntriesQuery,
    RunGoldQaDatasetEvaluationCommand,
)
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
            started = perf_counter()
            pipeline = self._rag.inspect_pipeline(
                project,
                entry.question,
                [],
                enable_query_rewrite_override=command.enable_query_rewrite,
                enable_hybrid_retrieval_override=command.enable_hybrid_retrieval,
            )

            answer = ""
            answer_generation_ms = 0.0
            if pipeline is not None:
                gen_started = perf_counter()
                answer = self._rag.generate_answer_from_pipeline(
                    project=project,
                    pipeline=pipeline,
                )
                answer_generation_ms = (perf_counter() - gen_started) * 1000.0

            latency_ms = (perf_counter() - started) * 1000.0
            latency_dict = None
            if pipeline is not None:
                full_latency = merge_with_answer_stage(
                    pipeline.latency,
                    answer_generation_ms=answer_generation_ms,
                    total_ms=latency_ms,
                )
                latency_dict = full_latency.to_dict()
                pipeline.latency = latency_dict
                pipeline.latency_ms = latency_ms

            return {
                "pipeline": pipeline,
                "answer": answer,
                "latency_ms": latency_ms,
                "latency": latency_dict,
            }

        return self._evaluation.evaluate_gold_qa_dataset(
            entries=entries,
            pipeline_runner=pipeline_runner,
        )
