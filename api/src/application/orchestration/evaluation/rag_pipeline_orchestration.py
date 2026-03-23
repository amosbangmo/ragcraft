"""
**Evaluation mode** orchestration: inspect-shaped pipeline (no product query log) + answer + latency merge.

Single canonical path for benchmark/manual-style runs:
:class:`~application.use_cases.evaluation.run_manual_evaluation.RunManualEvaluationUseCase` and
gold-QA execution call this function with :class:`~application.use_cases.chat.pipeline_use_case_ports.InspectRagPipelinePort`
(so ``emit_query_log=False`` on the shared build port). Product **ask** remains
:class:`~application.use_cases.chat.ask_question.AskQuestionUseCase` only.
"""

from __future__ import annotations

from time import perf_counter

from application.dto.rag.evaluation_pipeline import RagEvaluationPipelineInput
from application.use_cases.chat.pipeline_use_case_ports import (
    GenerateAnswerFromPipelinePort,
    InspectRagPipelinePort,
)
from domain.rag.pipeline_latency import PipelineLatency, merge_with_answer_stage
from domain.rag.rag_inspect_answer_run import RagInspectAnswerRun


def execute_rag_inspect_then_answer_for_evaluation(
    *,
    inspect_pipeline: InspectRagPipelinePort,
    generate_answer_from_pipeline: GenerateAnswerFromPipelinePort,
    params: RagEvaluationPipelineInput,
) -> RagInspectAnswerRun:
    """Run inspect use case, optionally generate an answer, merge latency onto the pipeline object."""
    started = perf_counter()
    pipeline = inspect_pipeline.execute(
        params.project,
        params.question,
        [],
        enable_query_rewrite_override=params.enable_query_rewrite,
        enable_hybrid_retrieval_override=params.enable_hybrid_retrieval,
    )
    answer = ""
    answer_generation_ms = 0.0
    if pipeline is not None:
        gen_started = perf_counter()
        answer = generate_answer_from_pipeline.execute(project=params.project, pipeline=pipeline)
        answer_generation_ms = (perf_counter() - gen_started) * 1000.0
    latency_ms = (perf_counter() - started) * 1000.0
    full_latency: PipelineLatency | None = None
    if pipeline is not None:
        merged = merge_with_answer_stage(
            pipeline.latency,
            answer_generation_ms=answer_generation_ms,
            total_ms=latency_ms,
        )
        full_latency = merged
        pipeline.latency = merged
        pipeline.latency_ms = latency_ms

    return RagInspectAnswerRun(
        pipeline=pipeline,
        answer=answer,
        latency_ms=latency_ms,
        full_latency=full_latency,
    )
