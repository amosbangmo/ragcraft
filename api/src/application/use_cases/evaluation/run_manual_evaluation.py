"""One-off manual evaluation for a single question (``POST /evaluation/manual`` and in-process clients).

This is the **only** application orchestration entry for manual eval: it always runs
:class:`~application.use_cases.evaluation.rag_pipeline_orchestration.execute_rag_inspect_then_answer_for_evaluation`
then :meth:`~domain.common.ports.manual_evaluation_from_rag_port.ManualEvaluationFromRagPort.build_manual_evaluation_result`.
"""

from __future__ import annotations

from domain.evaluation.manual_evaluation_result import ManualEvaluationResult
from application.dto.evaluation import RunManualEvaluationCommand
from application.use_cases.chat.pipeline_use_case_ports import (
    GenerateAnswerFromPipelinePort,
    InspectRagPipelinePort,
)
from application.dto.rag.evaluation_pipeline import RagEvaluationPipelineInput
from application.orchestration.evaluation.rag_pipeline_orchestration import (
    execute_rag_inspect_then_answer_for_evaluation,
)
from domain.common.ports.manual_evaluation_from_rag_port import ManualEvaluationFromRagPort
from domain.common.ports.project_workspace_port import ProjectWorkspacePort


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

        run = execute_rag_inspect_then_answer_for_evaluation(
            inspect_pipeline=self._inspect_pipeline,
            generate_answer_from_pipeline=self._generate_answer_from_pipeline,
            params=RagEvaluationPipelineInput(
                project=project,
                question=q,
                enable_query_rewrite=command.enable_query_rewrite_override,
                enable_hybrid_retrieval=command.enable_hybrid_retrieval_override,
            ),
        )

        return self._manual_evaluation.build_manual_evaluation_result(
            user_id=command.user_id,
            project_id=command.project_id,
            question=q,
            expected_answer=exp_ans,
            expected_doc_ids=exp_docs,
            expected_sources=exp_src,
            pipeline=run.pipeline,
            answer=run.answer,
            latency_ms=run.latency_ms,
            full_latency=run.full_latency,
        )
