from __future__ import annotations

from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.ports import GenerationPort


class GenerateAnswerFromPipelineUseCase:
    """LLM answer generation from an already-built pipeline (evaluation / gold QA paths)."""

    def __init__(self, *, generation: GenerationPort) -> None:
        self._generation = generation

    def execute(self, *, project: Project, pipeline: PipelineBuildResult) -> str:
        return self._generation.generate_answer(project=project, pipeline=pipeline)
