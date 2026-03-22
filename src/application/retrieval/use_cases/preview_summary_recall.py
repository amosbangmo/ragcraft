"""Backward-compatible import path; prefer :mod:`src.application.chat.use_cases.preview_summary_recall`."""

from src.application.chat.use_cases.preview_summary_recall import PreviewSummaryRecallUseCase

__all__ = ["PreviewSummaryRecallUseCase"]
