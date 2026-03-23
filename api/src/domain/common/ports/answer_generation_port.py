"""LLM answer text from a built RAG pipeline."""

from __future__ import annotations

from typing import Protocol, TypeAlias, runtime_checkable

from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult


@runtime_checkable
class AnswerGenerationPort(Protocol):
    def generate_answer(self, *, project: Project, pipeline: PipelineBuildResult) -> str: ...


GenerationPort: TypeAlias = AnswerGenerationPort
"""LLM answer generation from a built pipeline (preferred name at the RAG generation boundary)."""


__all__ = ["AnswerGenerationPort", "GenerationPort"]
