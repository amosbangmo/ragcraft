from __future__ import annotations

from domain.common.ports import GenerationPort
from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult


class GenerateAnswerFromPipelineUseCase:
    """LLM answer generation from an already-built pipeline (evaluation / gold QA paths)."""

    def __init__(self, *, generation: GenerationPort) -> None:
        self._generation = generation

    def execute(self, *, project: Project, pipeline: PipelineBuildResult) -> str:
        return self._generation.generate_answer(project=project, pipeline=pipeline)
