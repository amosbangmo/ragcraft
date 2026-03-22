"""LLM answer text from a built RAG pipeline."""

from __future__ import annotations

from typing import Protocol, TypeAlias, runtime_checkable

from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project


@runtime_checkable
class AnswerGenerationPort(Protocol):
    def generate_answer(self, *, project: Project, pipeline: PipelineBuildResult) -> str: ...


GenerationPort: TypeAlias = AnswerGenerationPort
"""LLM answer generation from a built pipeline (preferred name at the RAG generation boundary)."""


__all__ = ["AnswerGenerationPort", "GenerationPort"]
