"""
RAG mode separation and query-log contracts (application layer).

Enforces: ask may emit product query logs; inspect, evaluation, and preview must not
use the production ask/deferred logging path on the shared build port.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from application.dto.rag.evaluation_pipeline import RagEvaluationPipelineInput
from application.orchestration.evaluation.rag_pipeline_orchestration import (
    execute_rag_inspect_then_answer_for_evaluation,
)
from application.orchestration.rag.pipeline_query_log_emitter import PipelineQueryLogEmitter
from application.use_cases.chat.build_rag_pipeline import BuildRagPipelineUseCase
from application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
from application.use_cases.chat.preview_summary_recall import PreviewSummaryRecallUseCase
from domain.projects.project import Project
from domain.rag.pipeline_latency import PipelineLatency
from domain.rag.pipeline_payloads import PipelineBuildResult, SummaryRecallResult
from domain.rag.query_intent import QueryIntent
from domain.rag.retrieval_settings import RetrievalSettings
from domain.rag.retrieval_strategy import RetrievalStrategy
from domain.rag.summary_recall_document import SummaryRecallDocument


def _minimal_settings() -> RetrievalSettings:
    return RetrievalSettings(
        enable_query_rewrite=True,
        enable_hybrid_retrieval=False,
        similarity_search_k=5,
        bm25_search_k=5,
        hybrid_search_k=5,
        max_prompt_assets=5,
        bm25_k1=1.5,
        bm25_b=0.75,
        bm25_epsilon=0.25,
        rrf_k=60,
        hybrid_beta=0.5,
        max_text_chars_per_asset=4000,
        max_table_chars_per_asset=4000,
        query_rewrite_max_history_messages=6,
        enable_contextual_compression=False,
        enable_section_expansion=False,
        section_expansion_neighbor_window=2,
        section_expansion_max_per_section=12,
        section_expansion_global_max=64,
    )


def _minimal_recall_bundle() -> SummaryRecallResult:
    doc = SummaryRecallDocument(page_content="s", metadata={"doc_id": "d1"})
    return SummaryRecallResult(
        settings=_minimal_settings(),
        rewritten_question="rq",
        query_rewrite_ms=0.0,
        query_intent=QueryIntent.FACTUAL,
        table_aware_qa_enabled=False,
        use_adaptive_retrieval=False,
        strategy=RetrievalStrategy(k=5, use_hybrid=False, apply_filters=True),
        enable_hybrid_retrieval=False,
        enable_query_rewrite=True,
        filters_for_retrieval=None,
        vector_summary_docs=[doc],
        bm25_summary_docs=[],
        recalled_summary_docs=[doc],
        retrieval_ms=0.0,
    )


def test_build_rag_pipeline_passes_emit_query_log_to_emitter() -> None:
    recall = _minimal_recall_bundle()
    summary = MagicMock()
    summary.summary_recall_stage.return_value = recall
    assembly = MagicMock()
    built = PipelineBuildResult(question="q", latency=PipelineLatency())
    assembly.build.return_value = built
    emitter = MagicMock()
    uc = BuildRagPipelineUseCase(
        summary_recall_service=summary,
        pipeline_assembly_service=assembly,
        query_log_emitter=emitter,
    )
    project = Project(user_id="u", project_id="p")

    uc.execute(project, "q", emit_query_log=True)
    emitter.emit_after_pipeline_build.assert_called_once()
    assert emitter.emit_after_pipeline_build.call_args.kwargs["enabled"] is True

    emitter.reset_mock()
    uc.execute(project, "q2", emit_query_log=False)
    emitter.emit_after_pipeline_build.assert_called_once()
    assert emitter.emit_after_pipeline_build.call_args.kwargs["enabled"] is False


def test_pipeline_query_log_emitter_no_write_when_disabled_or_no_port() -> None:
    built = PipelineBuildResult(question="q", latency=PipelineLatency())
    project = Project(user_id="u", project_id="p")
    query_log = MagicMock()

    PipelineQueryLogEmitter(None).emit_after_pipeline_build(
        enabled=True, project=project, question="q", payload=built
    )
    PipelineQueryLogEmitter(query_log).emit_after_pipeline_build(
        enabled=False, project=project, question="q", payload=built
    )
    query_log.log_query.assert_not_called()


def test_inspect_rag_pipeline_always_sets_emit_query_log_false() -> None:
    retrieval = MagicMock()
    retrieval.execute.return_value = PipelineBuildResult(latency=PipelineLatency())
    inspect = InspectRagPipelineUseCase(retrieval=retrieval)
    project = Project(user_id="u", project_id="p")

    inspect.execute(project, "question")

    assert retrieval.execute.call_args.kwargs["emit_query_log"] is False


def test_evaluation_orchestration_routes_through_inspect_contract_no_build_stage_log() -> None:
    """Gold/manual eval uses InspectRagPipelineUseCase → BuildRagPipeline with logging off."""
    retrieval = MagicMock()
    retrieval.execute.return_value = PipelineBuildResult(
        question="q?",
        latency=PipelineLatency(retrieval_ms=1.0),
    )
    inspect = InspectRagPipelineUseCase(retrieval=retrieval)
    generate = MagicMock()
    generate.execute.return_value = "eval answer"
    project = Project(user_id="u", project_id="p")

    run = execute_rag_inspect_then_answer_for_evaluation(
        inspect_pipeline=inspect,
        generate_answer_from_pipeline=generate,
        params=RagEvaluationPipelineInput(
            project=project,
            question="q?",
            enable_query_rewrite=True,
            enable_hybrid_retrieval=False,
        ),
    )

    assert run.answer == "eval answer"
    retrieval.execute.assert_called_once()
    assert retrieval.execute.call_args.kwargs["emit_query_log"] is False


def test_preview_only_invokes_summary_recall_not_full_pipeline_build() -> None:
    recall = _minimal_recall_bundle()
    summary = MagicMock()
    summary.summary_recall_stage.return_value = recall
    uc = PreviewSummaryRecallUseCase(summary_recall_service=summary)
    project = Project(user_id="u", project_id="p")

    dto = uc.execute(project, "question")

    assert dto is not None
    summary.summary_recall_stage.assert_called_once()
