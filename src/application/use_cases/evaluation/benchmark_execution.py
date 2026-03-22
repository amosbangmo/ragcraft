"""Orchestrate gold QA benchmark runs: per-row evaluation, summary, correlations, failure and debug reports."""

from __future__ import annotations

import logging

from src.domain.benchmark_result import BenchmarkResult, BenchmarkRow, BenchmarkSummary
from src.domain.evaluation.benchmark_accumulator import BenchmarkAccumulator
from src.domain.multimodal_metrics import aggregate_multimodal_metrics
from src.domain.ports.benchmark_orchestration_ports import (
    AutoDebugSuggestionsPort,
    BenchmarkFailureAnalysisPort,
    BenchmarkRowProcessingPort,
    BenchmarkSummaryAggregationPort,
    CorrelationComputePort,
    ExplainabilityBuildPort,
)

logger = logging.getLogger(__name__)


class BenchmarkExecutionUseCase:
    def __init__(
        self,
        *,
        row_evaluation: BenchmarkRowProcessingPort,
        aggregation: BenchmarkSummaryAggregationPort,
        correlation: CorrelationComputePort,
        failure_analysis: BenchmarkFailureAnalysisPort,
        explainability: ExplainabilityBuildPort,
        auto_debug: AutoDebugSuggestionsPort,
    ) -> None:
        self._row_eval = row_evaluation
        self._aggregation = aggregation
        self._correlation_service = correlation
        self._failure_analysis_service = failure_analysis
        self._explainability_service = explainability
        self._auto_debug_service = auto_debug

    def _attach_explainability(self, row_payload: dict) -> None:
        explain = self._explainability_service.build_explanation(row_payload)
        row_payload["explanations"] = explain.get("explanations", [])
        row_payload["suggestions"] = explain.get("suggestions", [])

    def execute(self, *, entries, pipeline_runner) -> BenchmarkResult:
        acc = BenchmarkAccumulator()

        for entry in entries:
            result = pipeline_runner(entry)
            self._row_eval.process_row(entry, result, acc)

        summary_payload = self._aggregation.build_summary_payload(acc)
        rows = acc.rows

        failed_queries = len(rows) - acc.successful_queries
        logger.info(
            "Evaluation summary: %s/%s successful queries (%s pipeline failures)",
            acc.successful_queries,
            len(rows),
            failed_queries,
        )
        if acc.hallucination_flags:
            logger.info(
                "Evaluation: hallucination flag rate=%s",
                summary_payload.get("hallucination_rate"),
            )
        if acc.groundedness_values:
            low_g = sum(1 for g in acc.groundedness_values if float(g) < 0.5)
            logger.info(
                "Evaluation: %s/%s successful rows with groundedness_score < 0.5",
                low_g,
                len(acc.groundedness_values),
            )
        retr_low = 0
        retr_den = 0
        for r in rows:
            d = r.data
            ex = int(d.get("expected_doc_ids_count") or 0)
            rc = d.get("recall_at_k")
            if ex > 0 and rc is not None:
                retr_den += 1
                if float(rc) < 0.5:
                    retr_low += 1
        if retr_den > 0:
            logger.info(
                "Evaluation: recall@k < 0.5 on %s/%s rows with expected doc IDs",
                retr_low,
                retr_den,
            )

        correlation_rows = [dict(r.data) for r in rows]
        correlations = self._correlation_service.compute(correlation_rows)

        row_dicts = [row.to_dict() for row in rows]
        failure_full = self._failure_analysis_service.analyze(row_dicts)
        row_failure_meta = failure_full.get("row_failures") or []
        failures_report = {k: v for k, v in failure_full.items() if k != "row_failures"}

        rebuilt: list[BenchmarkRow] = []
        for idx, row in enumerate(rows):
            meta = row_failure_meta[idx] if idx < len(row_failure_meta) else {}
            labels = meta.get("failure_labels") if isinstance(meta, dict) else None
            crit = meta.get("failure_critical") if isinstance(meta, dict) else None
            if not isinstance(labels, list):
                labels = []
            d = dict(row.data)
            d["failure_labels"] = list(labels)
            d["failure_critical"] = bool(crit) if crit is not None else False
            self._attach_explainability(d)
            rebuilt.append(
                BenchmarkRow(entry_id=row.entry_id, question=row.question, data=d)
            )

        row_dicts_final = [row.to_dict() for row in rebuilt]
        mm_raw = aggregate_multimodal_metrics(row_dicts_final)
        multimodal_metrics = None
        if mm_raw and mm_raw.get("has_multimodal_assets"):
            multimodal_metrics = dict(mm_raw)

        auto_debug = self._auto_debug_service.build_suggestions(
            summary_payload,
            failures_report,
        )

        return BenchmarkResult(
            summary=BenchmarkSummary(data=summary_payload),
            rows=rebuilt,
            correlations=correlations,
            failures=failures_report,
            multimodal_metrics=multimodal_metrics,
            auto_debug=auto_debug,
        )
