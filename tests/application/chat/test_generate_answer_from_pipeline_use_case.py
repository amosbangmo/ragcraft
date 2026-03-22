from __future__ import annotations

from unittest.mock import MagicMock

from src.application.chat.use_cases.generate_answer_from_pipeline import GenerateAnswerFromPipelineUseCase
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project


def test_execute_delegates_to_answer_service() -> None:
    ag = MagicMock()
    ag.generate_answer.return_value = "answer text"
    uc = GenerateAnswerFromPipelineUseCase(answer_generation_service=ag)
    project = Project(user_id="u", project_id="p")
    pipeline = MagicMock(spec=PipelineBuildResult)

    out = uc.execute(project=project, pipeline=pipeline)

    assert out == "answer text"
    ag.generate_answer.assert_called_once_with(project=project, pipeline=pipeline)
