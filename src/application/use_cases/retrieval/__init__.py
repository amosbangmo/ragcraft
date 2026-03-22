"""Retrieval-side application orchestration (e.g. FAISS vs hybrid comparison)."""

from __future__ import annotations

from src.application.use_cases.retrieval.compare_retrieval_modes import CompareRetrievalModesUseCase

__all__ = ["CompareRetrievalModesUseCase"]
