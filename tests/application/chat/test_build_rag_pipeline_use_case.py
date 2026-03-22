from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.application.use_cases.chat.orchestration.pipeline_query_log_emitter import PipelineQueryLogEmitter
from src.application.use_cases.chat.build_rag_pipeline import BuildRagPipelineUseCase
from src.domain.project import Project


def test_build_invokes_emitter_when_payload_present() -> None:
    project = Project(user_id="u1", project_id="p1")
    payload = MagicMock()
    payload.latency = {"total_ms": 0.0}

    summary = MagicMock()
    assembly = MagicMock()
    emitter = MagicMock(spec=PipelineQueryLogEmitter)

    with patch(
        "src.application.use_cases.chat.build_rag_pipeline.run_recall_then_assemble_pipeline",
        return_value=payload,
    ) as run:
        uc = BuildRagPipelineUseCase(
            summary_recall_service=summary,
            pipeline_assembly_service=assembly,
            query_log_emitter=emitter,
        )
        out = uc.execute(project, "q", [], emit_query_log=True)

    assert out is payload
    run.assert_called_once()
    emitter.emit_after_pipeline_build.assert_called_once()
    call_kw = emitter.emit_after_pipeline_build.call_args.kwargs
    assert call_kw["enabled"] is True
    assert call_kw["question"] == "q"
    assert call_kw["payload"] is payload


def test_build_skips_emitter_when_no_payload() -> None:
    project = Project(user_id="u1", project_id="p1")
    emitter = MagicMock(spec=PipelineQueryLogEmitter)

    with patch(
        "src.application.use_cases.chat.build_rag_pipeline.run_recall_then_assemble_pipeline",
        return_value=None,
    ):
        uc = BuildRagPipelineUseCase(
            summary_recall_service=MagicMock(),
            pipeline_assembly_service=MagicMock(),
            query_log_emitter=emitter,
        )
        assert uc.execute(project, "q") is None

    emitter.emit_after_pipeline_build.assert_not_called()
