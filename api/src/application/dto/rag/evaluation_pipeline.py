"""Typed input for evaluation-only inspect+answer orchestration (no production query log)."""

from __future__ import annotations

from dataclasses import dataclass

from domain.projects.project import Project


@dataclass(frozen=True, slots=True)
class RagEvaluationPipelineInput:
    project: Project
    question: str
    enable_query_rewrite: bool | None
    enable_hybrid_retrieval: bool | None
