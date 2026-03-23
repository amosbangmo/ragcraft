from __future__ import annotations

from unittest.mock import MagicMock

from application.use_cases.chat.generate_answer_from_pipeline import GenerateAnswerFromPipelineUseCase
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.projects.project import Project


def test_execute_delegates_to_answer_service() -> None:
    ag = MagicMock()
    ag.generate_answer.return_value = "answer text"
    uc = GenerateAnswerFromPipelineUseCase(generation=ag)
    project = Project(user_id="u", project_id="p")
    pipeline = MagicMock(spec=PipelineBuildResult)

    out = uc.execute(project=project, pipeline=pipeline)

    assert out == "answer text"
    ag.generate_answer.assert_called_once_with(project=project, pipeline=pipeline)
