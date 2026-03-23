from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from application.orchestration.rag.summary_recall_ports import SummaryRecallTechnicalPorts
from application.orchestration.rag.summary_recall_workflow import ApplicationSummaryRecallStage
from domain.projects.project import Project
from domain.rag.retrieval_settings import RetrievalSettings
from infrastructure.config.config import RETRIEVAL_CONFIG


def _base_settings() -> RetrievalSettings:
    return RetrievalSettings.from_object(RETRIEVAL_CONFIG)


def test_query_rewrite_port_skipped_when_disabled() -> None:
    tuner = MagicMock()
    s = replace(_base_settings(), enable_query_rewrite=False)
    tuner.from_project.return_value = s
    tuner.merge.return_value = s

    qr = MagicMock()
    vec = MagicMock()
    vec.similarity_search.return_value = []
    lex = MagicMock()
    ports = SummaryRecallTechnicalPorts(
        query_rewrite=qr,
        vector_recall=vec,
        lexical_recall=lex,
    )
    stage = ApplicationSummaryRecallStage(settings_tuner=tuner, technical_ports=ports)
    project = Project(user_id="u1", project_id="p1")

    stage.summary_recall_stage(project, "hello", [])

    qr.rewrite.assert_not_called()
    vec.similarity_search.assert_called()


def test_query_rewrite_port_invoked_when_enabled() -> None:
    tuner = MagicMock()
    s = replace(_base_settings(), enable_query_rewrite=True)
    tuner.from_project.return_value = s
    tuner.merge.return_value = s

    qr = MagicMock()
    qr.rewrite.return_value = "rewritten_q"
    vec = MagicMock()
    vec.similarity_search.return_value = []
    lex = MagicMock()
    ports = SummaryRecallTechnicalPorts(
        query_rewrite=qr,
        vector_recall=vec,
        lexical_recall=lex,
    )
    stage = ApplicationSummaryRecallStage(settings_tuner=tuner, technical_ports=ports)
    project = Project(user_id="u1", project_id="p1")

    out = stage.summary_recall_stage(project, "hello", ["prev"])

    qr.rewrite.assert_called_once()
    assert out.rewritten_question == "rewritten_q"


@pytest.mark.parametrize(
    ("override_hybrid", "expect_adaptive"),
    [
        (None, True),
        (True, False),
        (False, False),
    ],
)
def test_adaptive_flag_follows_hybrid_override(
    override_hybrid: bool | None, expect_adaptive: bool
) -> None:
    tuner = MagicMock()
    s = _base_settings()
    tuner.from_project.return_value = s
    tuner.merge.return_value = s

    qr = MagicMock()
    qr.rewrite.return_value = "q"
    vec = MagicMock()
    vec.similarity_search.return_value = []
    lex = MagicMock()
    ports = SummaryRecallTechnicalPorts(
        query_rewrite=qr,
        vector_recall=vec,
        lexical_recall=lex,
    )
    stage = ApplicationSummaryRecallStage(settings_tuner=tuner, technical_ports=ports)
    project = Project(user_id="u1", project_id="p1")

    out = stage.summary_recall_stage(
        project,
        "hello",
        [],
        enable_hybrid_retrieval_override=override_hybrid,
    )

    assert out.use_adaptive_retrieval is expect_adaptive
