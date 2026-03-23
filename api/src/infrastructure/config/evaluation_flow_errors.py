"""Shared user-facing error strings for evaluation flows (manual + dataset)."""

from __future__ import annotations

from infrastructure.config.error_utils import get_user_error_message
from infrastructure.config.exceptions import DocStoreError, LLMServiceError, VectorStoreError


def map_evaluation_flow_exception(exc: Exception, *, dataset_evaluation: bool = False) -> str:
    """
    Map infrastructure exceptions to concise, accurate copy.

    Distinguishes vector / doc-store / LLM failures from generic unexpected errors.
    """
    if isinstance(exc, VectorStoreError):
        fallback = (
            "Unable to query the FAISS index for dataset evaluation."
            if dataset_evaluation
            else "Unable to query the FAISS index for this evaluation."
        )
        return get_user_error_message(exc, fallback)
    if isinstance(exc, DocStoreError):
        fallback = (
            "Unable to read supporting assets from SQLite during dataset evaluation."
            if dataset_evaluation
            else "Unable to retrieve supporting assets from SQLite for this evaluation."
        )
        return get_user_error_message(exc, fallback)
    if isinstance(exc, LLMServiceError):
        fallback = (
            "The language model failed while running dataset evaluation (retrieval or answer generation)."
            if dataset_evaluation
            else "The language model failed while generating the evaluation answer."
        )
        return get_user_error_message(exc, fallback)
    ctx = "dataset evaluation" if dataset_evaluation else "manual evaluation"
    return get_user_error_message(exc, f"Unexpected error during {ctx}: {exc}")
