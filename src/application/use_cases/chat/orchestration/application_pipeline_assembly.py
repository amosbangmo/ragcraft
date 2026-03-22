"""Application implementation of :class:`~src.application.use_cases.chat.orchestration.ports.PipelineAssemblyPort`."""

from __future__ import annotations

from dataclasses import dataclass

from src.application.use_cases.chat.orchestration.assemble_pipeline_from_recall import (
    assemble_pipeline_from_recall,
)
from src.application.use_cases.chat.orchestration.ports import PostRecallStagePorts
from src.domain.pipeline_payloads import PipelineBuildResult, SummaryRecallResult
from src.domain.project import Project


@dataclass
class ApplicationPipelineAssembly:
    """
    Delegates ``build`` to :func:`~src.application.use_cases.chat.orchestration.assemble_pipeline_from_recall.assemble_pipeline_from_recall`.
    """

    stages: PostRecallStagePorts

    def build(
        self,
        *,
        project: Project,
        question: str,
        chat_history: list[str],
        recall: SummaryRecallResult,
        pipeline_started_monotonic: float,
    ) -> PipelineBuildResult | None:
        return assemble_pipeline_from_recall(
            project=project,
            question=question,
            chat_history=chat_history,
            recall=recall,
            pipeline_started_monotonic=pipeline_started_monotonic,
            stages=self.stages,
        )


def is_pipeline_assembly_port(obj: object) -> bool:
    """Structural check for tests (duck-typing :class:`PipelineAssemblyPort`)."""
    build = getattr(obj, "build", None)
    return callable(build)
