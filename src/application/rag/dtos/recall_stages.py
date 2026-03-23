"""Typed intermediate results for summary-recall orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.summary_recall_document import SummaryRecallDocument


@dataclass(frozen=True, slots=True)
class VectorLexicalRecallBundle:
    """Vector (+ optional lexical) summary recall before RRF merge materializes ``recalled_summary_docs``."""

    vector_summary_docs: tuple[SummaryRecallDocument, ...]
    bm25_summary_docs: tuple[SummaryRecallDocument, ...]
    recalled_summary_docs: tuple[SummaryRecallDocument, ...]
