"""Lightweight timing smoke: mocked RAG ask stays within a generous wall-clock bound."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from application.use_cases.chat.ask_question import AskQuestionUseCase
from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult


def test_mocked_ask_question_completes_quickly() -> None:
    pipeline = PipelineBuildResult()
    retrieval = MagicMock()
    retrieval.execute.return_value = pipeline
    generation = MagicMock()
    generation.generate_answer.return_value = "ok"

    ask = AskQuestionUseCase(retrieval=retrieval, generation=generation, query_log=None)
    project = Project(user_id="u", project_id="p")

    t0 = time.perf_counter()
    out = ask.execute(project, "hello", [])
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert out is not None
    assert out.answer == "ok"
    assert elapsed_ms < 500.0
