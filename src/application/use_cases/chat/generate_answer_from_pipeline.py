from __future__ import annotations

from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.infrastructure.services.answer_generation_service import AnswerGenerationService


class GenerateAnswerFromPipelineUseCase:
    """LLM answer generation from an already-built pipeline (evaluation / gold QA paths)."""

    def __init__(self, *, answer_generation_service: AnswerGenerationService) -> None:
        self._answer_generation = answer_generation_service

    def execute(self, *, project: Project, pipeline: PipelineBuildResult) -> str:
        return self._answer_generation.generate_answer(project=project, pipeline=pipeline)
