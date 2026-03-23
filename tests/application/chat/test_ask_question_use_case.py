from __future__ import annotations

from unittest.mock import MagicMock

from src.application.use_cases.chat.ask_question import AskQuestionUseCase
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec


def test_ask_returns_none_when_no_pipeline() -> None:
    retrieval = MagicMock()
    retrieval.execute.return_value = None
    gen = MagicMock()
    uc = AskQuestionUseCase(retrieval=retrieval, generation=gen, query_log=None)
    project = Project(user_id="u", project_id="p")

    assert uc.execute(project, "q?") is None
    gen.generate_answer.assert_not_called()


def test_ask_success_without_query_log() -> None:
    pipeline = PipelineBuildResult(question="q?", latency={"retrieval_ms": 1.0})
    retrieval = MagicMock()
    retrieval.execute.return_value = pipeline
    gen = MagicMock()
    gen.generate_answer.return_value = "the answer"
    uc = AskQuestionUseCase(retrieval=retrieval, generation=gen, query_log=None)
    project = Project(user_id="u", project_id="p")

    resp = uc.execute(project, "q?")

    assert resp is not None
    assert resp.answer == "the answer"
    assert resp.question == "q?"
    gen.generate_answer.assert_called_once_with(project=project, pipeline=pipeline)
    retrieval.execute.assert_called_once()
    call_kw = retrieval.execute.call_args[1]
    assert call_kw["emit_query_log"] is True


def test_retrieval_overrides_passed_to_retrieval_port() -> None:
    pipeline = PipelineBuildResult(latency={})
    retrieval = MagicMock()
    retrieval.execute.return_value = pipeline
    gen = MagicMock()
    gen.generate_answer.return_value = "x"
    uc = AskQuestionUseCase(retrieval=retrieval, generation=gen, query_log=None)
    project = Project(user_id="u", project_id="p")
    spec = RetrievalSettingsOverrideSpec.from_optional_mapping({"similarity_search_k": 9})
    assert spec is not None

    uc.execute(project, "q?", retrieval_overrides=spec)

    assert retrieval.execute.call_args[1]["retrieval_overrides"] is spec


def test_ask_logging_failure_still_returns_answer() -> None:
    pipeline = PipelineBuildResult(question="q?", latency={})
    retrieval = MagicMock()
    retrieval.execute.return_value = pipeline
    gen = MagicMock()
    gen.generate_answer.return_value = "ok"
    query_log = MagicMock()
    query_log.log_query.side_effect = RuntimeError("db down")
    uc = AskQuestionUseCase(retrieval=retrieval, generation=gen, query_log=query_log)
    project = Project(user_id="u", project_id="p")

    resp = uc.execute(project, "q?")

    assert resp is not None
    assert resp.answer == "ok"
    query_log.log_query.assert_called_once()
    assert retrieval.execute.call_args[1]["emit_query_log"] is False
