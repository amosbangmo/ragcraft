"""
Application orchestration for evaluation: inspect pipeline (no query log) + LLM answer + latency merge.

Used by manual evaluation and gold-QA dataset runs. Chat ``/chat/ask`` remains
:class:`~src.application.use_cases.chat.ask_question.AskQuestionUseCase` (build + answer + deferred log).
"""

from __future__ import annotations

from time import perf_counter

from src.application.use_cases.chat.pipeline_use_case_ports import (
    GenerateAnswerFromPipelinePort,
    InspectRagPipelinePort,
)
from src.domain.pipeline_latency import merge_with_answer_stage
from src.domain.project import Project
from src.domain.rag_inspect_answer_run import RagInspectAnswerRun


def execute_rag_inspect_then_answer_for_evaluation(
    *,
    inspect_pipeline: InspectRagPipelinePort,
    generate_answer_from_pipeline: GenerateAnswerFromPipelinePort,
    project: Project,
    question: str,
    enable_query_rewrite: bool | None,
    enable_hybrid_retrieval: bool | None,
) -> RagInspectAnswerRun:
    """Run inspect use case, optionally generate an answer, merge latency onto the pipeline object."""
    started = perf_counter()
    pipeline = inspect_pipeline.execute(
        project,
        question,
        [],
        enable_query_rewrite_override=enable_query_rewrite,
        enable_hybrid_retrieval_override=enable_hybrid_retrieval,
    )
    answer = ""
    answer_generation_ms = 0.0
    if pipeline is not None:
        gen_started = perf_counter()
        answer = generate_answer_from_pipeline.execute(project=project, pipeline=pipeline)
        answer_generation_ms = (perf_counter() - gen_started) * 1000.0
    latency_ms = (perf_counter() - started) * 1000.0
    full_latency: dict[str, float] | None = None
    if pipeline is not None:
        merged = merge_with_answer_stage(
            pipeline.latency,
            answer_generation_ms=answer_generation_ms,
            total_ms=latency_ms,
        )
        full_latency = merged.to_dict()
        pipeline.latency = full_latency
        pipeline.latency_ms = latency_ms

    return RagInspectAnswerRun(
        pipeline=pipeline,
        answer=answer,
        latency_ms=latency_ms,
        full_latency=full_latency,
    )
