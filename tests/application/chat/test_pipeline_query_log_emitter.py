from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.use_cases.chat.orchestration.pipeline_query_log_emitter import PipelineQueryLogEmitter
from src.domain.project import Project


@pytest.fixture
def project() -> Project:
    return Project(user_id="u1", project_id="p1")


def test_emitter_skips_when_disabled(project: Project) -> None:
    log = MagicMock()
    emitter = PipelineQueryLogEmitter(log)
    payload = MagicMock()
    payload.latency = {"total_ms": 1.0}
    emitter.emit_after_pipeline_build(
        enabled=False, project=project, question="q", payload=payload
    )
    log.log_query.assert_not_called()


def test_emitter_skips_when_no_service(project: Project) -> None:
    emitter = PipelineQueryLogEmitter(None)
    payload = MagicMock()
    payload.latency = {"total_ms": 1.0}
    emitter.emit_after_pipeline_build(
        enabled=True, project=project, question="q", payload=payload
    )


def test_emitter_logs_when_enabled(project: Project) -> None:
    log = MagicMock()
    emitter = PipelineQueryLogEmitter(log)
    payload = MagicMock()
    payload.latency = {
        "query_rewrite_ms": 0.0,
        "retrieval_ms": 0.0,
        "reranking_ms": 0.0,
        "prompt_build_ms": 0.0,
        "answer_generation_ms": 0.0,
        "total_ms": 1.0,
    }
    emitter.emit_after_pipeline_build(
        enabled=True, project=project, question="q", payload=payload
    )
    log.log_query.assert_called_once()
