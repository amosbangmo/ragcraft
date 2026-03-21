"""
Synthetic ``BenchmarkResult`` builders for tests (no LLM / no network).

Keeps regression checks decoupled from a real evaluation run.
"""

from __future__ import annotations

from typing import Any

from src.domain.benchmark_result import BenchmarkResult, BenchmarkRow, BenchmarkSummary

_DEFAULT_SUMMARY: dict[str, Any] = {
    "total_entries": 2,
    "successful_queries": 2,
    "entries_with_expected_doc_ids": 2,
    "entries_with_expected_sources": 2,
    "entries_with_expected_answers": 2,
    "avg_doc_id_recall": 1.0,
    "avg_source_recall": 1.0,
    "avg_precision_at_k": 1.0,
    "mrr": 1.0,
    "map": 1.0,
    "avg_confidence": 0.9,
    "avg_latency_ms": 12.0,
    "doc_id_hit_rate": 1.0,
    "source_hit_rate": 1.0,
    "answer_exact_match_rate": 1.0,
    "avg_answer_precision": 1.0,
    "avg_answer_recall": 1.0,
    "avg_answer_f1": 1.0,
    "avg_citation_doc_id_precision": 1.0,
    "avg_citation_doc_id_recall": 1.0,
    "avg_citation_doc_id_f1": 1.0,
    "avg_citation_source_precision": 1.0,
    "avg_citation_source_recall": 1.0,
    "avg_citation_source_f1": 1.0,
    "citation_doc_id_hit_rate": 1.0,
    "citation_source_hit_rate": 1.0,
}


def make_benchmark_result(
    *,
    summary_overrides: dict[str, Any] | None = None,
    rows: list[BenchmarkRow] | None = None,
) -> BenchmarkResult:
    summary_data = dict(_DEFAULT_SUMMARY)
    if summary_overrides:
        summary_data.update(summary_overrides)
    return BenchmarkResult(
        summary=BenchmarkSummary(data=summary_data),
        rows=list(rows) if rows is not None else [],
    )
