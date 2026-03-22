"""Backward-compatible import path; prefer :mod:`src.application.chat.use_cases.inspect_rag_pipeline`."""

from src.application.chat.use_cases.inspect_rag_pipeline import InspectRagPipelineUseCase as InspectPipelineUseCase

__all__ = ["InspectPipelineUseCase"]
