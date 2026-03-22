"""Backward-compatible import path; prefer :mod:`src.application.chat.use_cases.build_rag_pipeline`."""

from src.application.chat.use_cases.build_rag_pipeline import BuildRagPipelineUseCase as BuildPipelineUseCase

__all__ = ["BuildPipelineUseCase"]
