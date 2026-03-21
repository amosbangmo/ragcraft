from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkRunMetadata:
    """
    Run-level context attached to exported benchmark reports (JSON / CSV / Markdown).

    Distinct from per-row payloads: this captures when and how the evaluation was run.
    """

    project_id: str
    generated_at_utc: str
    enable_query_rewrite: bool
    enable_hybrid_retrieval: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "generated_at_utc": self.generated_at_utc,
            "enable_query_rewrite": self.enable_query_rewrite,
            "enable_hybrid_retrieval": self.enable_hybrid_retrieval,
        }


@dataclass(frozen=True)
class BenchmarkRow:
    """
    Structured per-entry benchmark result.

    The ``data`` payload intentionally stays flexible so the evaluation layer can
    evolve incrementally without forcing a broad refactor across the UI.

    Common LLM-judge fields include ``groundedness``, ``citation_faithfulness``,
    ``answer_relevance``, and ``hallucination_score`` (0–1 when configured), plus
    ``has_hallucination`` (boolean). The unified judge also adds
    ``groundedness_score``, ``citation_faithfulness_score``, and
    ``answer_relevance_score`` (mirrors of the above for explicit naming).
    """

    entry_id: int
    question: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "question": self.question,
            **dict(self.data),
        }


@dataclass(frozen=True)
class BenchmarkSummary:
    """
    Structured benchmark summary.

    As with ``BenchmarkRow``, the payload remains flexible on purpose. This lets
    the project move from dict-based evaluation to typed results without forcing
    every future metric to become a top-level dataclass field immediately.

    Aggregate judge metrics include ``avg_groundedness``,
    ``avg_citation_faithfulness``, ``avg_answer_relevance``, ``avg_hallucination_score``,
    and ``hallucination_rate`` (fraction of rows with ``has_hallucination`` true).
    """

    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.data)


@dataclass(frozen=True)
class BenchmarkResult:
    """
    Full benchmark result returned by the evaluation layer.

    This becomes the application contract between:
    - service layer
    - app facade
    - Streamlit UI
    - future export/report layers

    Optional ``correlations`` holds Pearson summaries from :class:`~src.services.correlation_service.CorrelationService`.
    Optional ``failures`` holds rule-based diagnostics from
    :class:`~src.services.failure_analysis_service.FailureAnalysisService` (counts, examples, etc.).
    """

    summary: BenchmarkSummary
    rows: list[BenchmarkRow] = field(default_factory=list)
    correlations: dict[str, Any] | None = None
    failures: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "summary": self.summary.to_dict(),
            "rows": [row.to_dict() for row in self.rows],
        }
        if self.correlations is not None:
            out["correlations"] = dict(self.correlations)
        if self.failures is not None:
            out["failures"] = dict(self.failures)
        return out

    @classmethod
    def from_plain_dict(cls, payload: dict[str, Any]) -> BenchmarkResult:
        """
        Rebuild from :meth:`to_dict` output (e.g. after Streamlit session_state round-trip).
        """
        summary_raw = payload.get("summary")
        if not isinstance(summary_raw, dict):
            summary_raw = {}
        rows_raw = payload.get("rows")
        if not isinstance(rows_raw, list):
            rows_raw = []
        summary = BenchmarkSummary(data=dict(summary_raw))
        rows: list[BenchmarkRow] = []
        reserved = frozenset({"entry_id", "question"})
        for item in rows_raw:
            if not isinstance(item, dict) or "entry_id" not in item:
                continue
            entry_id = int(item["entry_id"])
            q = item.get("question", "")
            question = q if isinstance(q, str) else str(q)
            data = {k: v for k, v in item.items() if k not in reserved}
            rows.append(BenchmarkRow(entry_id=entry_id, question=question, data=data))
        corr_raw = payload.get("correlations")
        correlations: dict[str, Any] | None = None
        if isinstance(corr_raw, dict):
            correlations = dict(corr_raw)
        fail_raw = payload.get("failures")
        failures: dict[str, Any] | None = None
        if isinstance(fail_raw, dict):
            failures = dict(fail_raw)
        return cls(summary=summary, rows=rows, correlations=correlations, failures=failures)


def coerce_benchmark_result(value: Any) -> BenchmarkResult | None:
    """
    Accept a canonical instance, a plain dict (session round-trip), or another
    ``BenchmarkResult`` class after Streamlit reload (same name, different type id).
    """
    if isinstance(value, BenchmarkResult):
        return value
    if isinstance(value, dict):
        try:
            return BenchmarkResult.from_plain_dict(value)
        except (TypeError, ValueError, KeyError):
            return None
    to_dict = getattr(value, "to_dict", None)
    if (
        type(value).__name__ == "BenchmarkResult"
        and callable(to_dict)
    ):
        try:
            dumped = to_dict()
            if isinstance(dumped, dict):
                return BenchmarkResult.from_plain_dict(dumped)
        except (TypeError, ValueError, KeyError):
            return None
    return None
