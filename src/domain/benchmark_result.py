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

    Metric families, comparison direction, and ``judge_failed`` semantics are summarized in
    :mod:`src.domain.benchmark_metric_taxonomy`.

    LLM-judge fields use canonical keys ``groundedness_score``,
    ``citation_faithfulness_score``, ``answer_relevance_score``,
    ``hallucination_score``, ``answer_correctness_score`` (0–1 when configured),
    and ``has_hallucination`` (boolean).
    Gold-answer embedding overlap uses ``semantic_similarity`` (cosine on local embeddings, 0–1).
    Ranking quality adds ``ndcg_at_k`` when ``expected_doc_ids`` exist (binary relevance).
    Prompt doc ID overlap metrics (``prompt_doc_id_*``) compare **prompt sources**
    (assets in the prompt) to gold ``expected_doc_ids``.
    Citation doc ID metrics (``citation_doc_id_*``, ``citation_doc_ids_count``) use
    **parsed** ``[Source N]`` labels in the generated answer mapped via ``prompt_sources``.
    ``judge_failed`` is true when the LLM judge used a failure fallback (not when the pipeline
    failed before judging). When true, judge numeric fields are ``None`` and ``judge_failure_reason``
    explains the failure (often the sentinel ``judge_failure`` from the judge service).
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

    See :mod:`src.domain.benchmark_metric_taxonomy` for how aggregates map to families and how
    ``judge_failed`` rows are excluded from judge means.

    Aggregate judge metrics use the same stem as per-row scores: ``avg_groundedness_score``,
    ``avg_citation_faithfulness_score``, ``avg_answer_relevance_score``,
    ``avg_answer_correctness``, ``avg_hallucination_score``, and ``hallucination_rate``
    (fraction of rows with ``has_hallucination`` true among rows where ``judge_failed`` is false).
    Retrieval summaries use
    ``avg_reciprocal_rank``, ``avg_average_precision``, and ``avg_ndcg_at_k``.
    Gold-answer embedding mean is ``avg_semantic_similarity`` (rows with expected answers only).
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

    Optional ``correlations`` holds Pearson summaries from :class:`~src.infrastructure.adapters.evaluation.correlation_service.CorrelationService`.
    Optional ``failures`` holds rule-based diagnostics from
    :class:`~src.domain.benchmark_failure_analysis.FailureAnalysisService` (counts, examples, etc.).
    Optional ``multimodal_metrics`` holds aggregates from modality-aware evaluation (usage rates, conditional scores).
    Optional ``auto_debug`` holds system-level suggestion cards from :class:`~src.infrastructure.adapters.evaluation.auto_debug_service.AutoDebugService`.
    Optional ``run_id`` identifies this benchmark run for comparison and history (e.g. short UUID).
    """

    summary: BenchmarkSummary
    rows: list[BenchmarkRow] = field(default_factory=list)
    correlations: dict[str, Any] | None = None
    failures: dict[str, Any] | None = None
    multimodal_metrics: dict[str, Any] | None = None
    auto_debug: list[dict[str, str]] | None = None
    run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "summary": self.summary.to_dict(),
            "rows": [row.to_dict() for row in self.rows],
        }
        if self.correlations is not None:
            out["correlations"] = dict(self.correlations)
        if self.failures is not None:
            out["failures"] = dict(self.failures)
        if self.multimodal_metrics is not None:
            out["multimodal_metrics"] = dict(self.multimodal_metrics)
        if self.auto_debug is not None:
            out["auto_debug"] = [dict(item) for item in self.auto_debug]
        if self.run_id is not None:
            out["run_id"] = self.run_id
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
        mm_raw = payload.get("multimodal_metrics")
        multimodal_metrics: dict[str, Any] | None = None
        if isinstance(mm_raw, dict):
            multimodal_metrics = dict(mm_raw)
        ad_raw = payload.get("auto_debug")
        auto_debug: list[dict[str, str]] | None = None
        if isinstance(ad_raw, list):
            parsed: list[dict[str, str]] = []
            for item in ad_raw:
                if not isinstance(item, dict):
                    continue
                t = item.get("title")
                d = item.get("description")
                if isinstance(t, str) and isinstance(d, str):
                    parsed.append({"title": t, "description": d})
            auto_debug = parsed
        rid_raw = payload.get("run_id")
        run_id: str | None = rid_raw if isinstance(rid_raw, str) and rid_raw.strip() else None
        return cls(
            summary=summary,
            rows=rows,
            correlations=correlations,
            failures=failures,
            multimodal_metrics=multimodal_metrics,
            auto_debug=auto_debug,
            run_id=run_id,
        )


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
