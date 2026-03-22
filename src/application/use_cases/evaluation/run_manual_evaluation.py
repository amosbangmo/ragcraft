"""One-off manual evaluation for a single question (``POST /evaluation/manual`` and in-process clients)."""

from __future__ import annotations

from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.application.evaluation.dtos import RunManualEvaluationCommand
from src.application.use_cases.evaluation.rag_answer_for_eval import run_rag_inspect_and_answer_for_eval
from src.infrastructure.services.evaluation_service import EvaluationService
from src.infrastructure.services.manual_evaluation_service import manual_evaluation_result_from_rag_outputs
from src.infrastructure.services.project_service import ProjectService
from src.infrastructure.services.rag_service import RAGService


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

        run = run_rag_inspect_and_answer_for_eval(
            rag_service=self._rag,
            project=project,
            question=q,
            enable_query_rewrite=command.enable_query_rewrite_override,
            enable_hybrid_retrieval=command.enable_hybrid_retrieval_override,
        )
        pipeline = run["pipeline"]
        answer = run["answer"]
        latency_ms = run["latency_ms"]
        full_latency_dict = run["latency"]

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
