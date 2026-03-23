"""Typed evaluation orchestration: inspect + answer without production query log."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.application.rag.dtos.evaluation_pipeline import RagEvaluationPipelineInput
from src.application.use_cases.evaluation.rag_pipeline_orchestration import (
    execute_rag_inspect_then_answer_for_evaluation,
)
from src.domain.pipeline_latency import PipelineLatency
from src.domain.project import Project


def test_evaluation_orchestration_merges_latency_when_pipeline_present() -> None:
    project = Project(user_id="u", project_id="p")
    pipeline = MagicMock()
    pipeline.latency = {"query_rewrite_ms": 1.0, "retrieval_ms": 2.0}

    inspect_pipeline = MagicMock()
    inspect_pipeline.execute.return_value = pipeline
    generate = MagicMock()
    generate.execute.return_value = "answer text"

    run = execute_rag_inspect_then_answer_for_evaluation(
        inspect_pipeline=inspect_pipeline,
        generate_answer_from_pipeline=generate,
        params=RagEvaluationPipelineInput(
            project=project,
            question="q?",
            enable_query_rewrite=True,
            enable_hybrid_retrieval=False,
        ),
    )

    assert run.answer == "answer text"
    assert run.pipeline is pipeline
    assert isinstance(run.full_latency, PipelineLatency)
    assert run.full_latency.answer_generation_ms >= 0.0
    inspect_pipeline.execute.assert_called_once()
    generate.execute.assert_called_once_with(project=project, pipeline=pipeline)


def test_evaluation_orchestration_no_pipeline_skips_generation() -> None:
    project = Project(user_id="u", project_id="p")
    inspect_pipeline = MagicMock()
    inspect_pipeline.execute.return_value = None
    generate = MagicMock()

    run = execute_rag_inspect_then_answer_for_evaluation(
        inspect_pipeline=inspect_pipeline,
        generate_answer_from_pipeline=generate,
        params=RagEvaluationPipelineInput(
            project=project,
            question="q?",
            enable_query_rewrite=None,
            enable_hybrid_retrieval=None,
        ),
    )

    assert run.pipeline is None
    assert run.answer == ""
    assert run.full_latency is None
    generate.execute.assert_not_called()
