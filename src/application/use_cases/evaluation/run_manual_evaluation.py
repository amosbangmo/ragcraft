"""One-off manual evaluation for a single question (``POST /evaluation/manual`` and in-process clients)."""

from __future__ import annotations

from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.application.evaluation.dtos import RunManualEvaluationCommand
from src.application.use_cases.chat.pipeline_use_case_ports import (
    GenerateAnswerFromPipelinePort,
    InspectRagPipelinePort,
)
from src.application.use_cases.evaluation.rag_answer_for_eval import run_rag_inspect_and_answer_for_eval
from src.domain.ports.manual_evaluation_from_rag_port import ManualEvaluationFromRagPort
from src.domain.ports.project_workspace_port import ProjectWorkspacePort


class RunManualEvaluationUseCase:
    def __init__(
        self,
        *,
        project_service: ProjectWorkspacePort,
        inspect_pipeline: InspectRagPipelinePort,
        generate_answer_from_pipeline: GenerateAnswerFromPipelinePort,
        manual_evaluation: ManualEvaluationFromRagPort,
    ) -> None:
        self._project_service = project_service
        self._inspect_pipeline = inspect_pipeline
        self._generate_answer_from_pipeline = generate_answer_from_pipeline
        self._manual_evaluation = manual_evaluation

    def execute(self, command: RunManualEvaluationCommand) -> ManualEvaluationResult:
        q = (command.question or "").strip()
        exp_ans = (command.expected_answer or "").strip() or None
        exp_docs = list(command.expected_doc_ids or [])
        exp_src = list(command.expected_sources or [])

        project = self._project_service.get_project(command.user_id, command.project_id)

        run = run_rag_inspect_and_answer_for_eval(
            inspect_pipeline=self._inspect_pipeline,
            generate_answer_from_pipeline=self._generate_answer_from_pipeline,
            project=project,
            question=q,
            enable_query_rewrite=command.enable_query_rewrite_override,
            enable_hybrid_retrieval=command.enable_hybrid_retrieval_override,
        )
        pipeline = run["pipeline"]
        answer = run["answer"]
        latency_ms = run["latency_ms"]
        full_latency_dict = run["latency"]

        return self._manual_evaluation.build_manual_evaluation_result(
            user_id=command.user_id,
            project_id=command.project_id,
            question=q,
            expected_answer=exp_ans,
            expected_doc_ids=exp_docs,
            expected_sources=exp_src,
            pipeline=pipeline,
            answer=answer,
            latency_ms=latency_ms,
            full_latency_dict=full_latency_dict,
        )
