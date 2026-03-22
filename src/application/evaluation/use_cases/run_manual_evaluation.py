"""One-off manual evaluation for a single question (parity with :meth:`RAGCraftApp.evaluate_manual_question`)."""

from __future__ import annotations

from time import perf_counter

from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.domain.pipeline_latency import merge_with_answer_stage
from src.application.evaluation.dtos import RunManualEvaluationCommand
from src.services.evaluation_service import EvaluationService
from src.services.manual_evaluation_service import manual_evaluation_result_from_rag_outputs
from src.services.project_service import ProjectService
from src.services.rag_service import RAGService


class RunManualEvaluationUseCase:
    def __init__(
        self,
        *,
        project_service: ProjectService,
        rag_service: RAGService,
        evaluation_service: EvaluationService,
    ) -> None:
        self._project_service = project_service
        self._rag = rag_service
        self._evaluation = evaluation_service

    def execute(self, command: RunManualEvaluationCommand) -> ManualEvaluationResult:
        q = (command.question or "").strip()
        exp_ans = (command.expected_answer or "").strip() or None
        exp_docs = list(command.expected_doc_ids or [])
        exp_src = list(command.expected_sources or [])

        project = self._project_service.get_project(command.user_id, command.project_id)

        started = perf_counter()
        pipeline = self._rag.inspect_pipeline(
            project,
            q,
            [],
            enable_query_rewrite_override=command.enable_query_rewrite_override,
            enable_hybrid_retrieval_override=command.enable_hybrid_retrieval_override,
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

        full_latency_dict = None
        if pipeline is not None:
            full_lat = merge_with_answer_stage(
                pipeline.latency,
                answer_generation_ms=answer_generation_ms,
                total_ms=latency_ms,
            )
            full_latency_dict = full_lat.to_dict()
            pipeline.latency = full_latency_dict
            pipeline.latency_ms = latency_ms

        return manual_evaluation_result_from_rag_outputs(
            user_id=command.user_id,
            project_id=command.project_id,
            q=q,
            exp_ans=exp_ans,
            exp_docs=exp_docs,
            exp_src=exp_src,
            pipeline=pipeline,
            answer=answer,
            latency_ms=latency_ms,
            full_latency_dict=full_latency_dict,
            evaluation_service=self._evaluation,
        )
