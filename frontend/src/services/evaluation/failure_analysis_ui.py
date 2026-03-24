"""Heuristic failure taxonomy over benchmark row dicts (frontend wire layer)."""

from __future__ import annotations

from typing import Any

FAILURE_LABEL_ORDER: tuple[str, ...] = (
    "retrieval_failure",
    "context_selection_failure",
    "citation_failure",
    "judge_failure",
    "grounding_failure",
    "hallucination",
    "low_relevance",
    "low_confidence",
    "table_misuse",
    "image_hallucination",
)

DEFAULT_QUALITY_THRESHOLD = 0.5
DEFAULT_HALLUCINATION_THRESHOLD = 0.5
DEFAULT_LOW_CONFIDENCE = 0.35
DEFAULT_HIGH_CONFIDENCE_DANGEROUS = 0.65
DEFAULT_TOP_EXAMPLES_PER_TYPE = 5


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"true", "1", "yes"}:
            return True
        if s in {"false", "0", "no"}:
            return False
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class FailureAnalysisService:
    def __init__(
        self,
        *,
        quality_threshold: float = DEFAULT_QUALITY_THRESHOLD,
        hallucination_threshold: float = DEFAULT_HALLUCINATION_THRESHOLD,
        low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE,
        high_confidence_dangerous: float = DEFAULT_HIGH_CONFIDENCE_DANGEROUS,
        top_examples_per_type: int = DEFAULT_TOP_EXAMPLES_PER_TYPE,
    ) -> None:
        self._q = quality_threshold
        self._hall = hallucination_threshold
        self._low_conf = low_confidence_threshold
        self._hi_conf_bad = high_confidence_dangerous
        self._top_n = max(0, int(top_examples_per_type))

    def analyze(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        row_failures: list[dict[str, Any]] = []
        counts: dict[str, int] = {k: 0 for k in FAILURE_LABEL_ORDER}
        examples: dict[str, list[dict[str, Any]]] = {k: [] for k in FAILURE_LABEL_ORDER}
        critical_count = 0

        for row in rows:
            labels, critical = self._classify_row(row)
            row_failures.append(
                {
                    "failure_labels": list(labels),
                    "failure_critical": bool(critical),
                }
            )
            if critical:
                critical_count += 1
            for lb in labels:
                counts[lb] = counts.get(lb, 0) + 1
                if self._top_n and len(examples.get(lb, [])) < self._top_n:
                    ex = self._example_record(row, labels, critical)
                    examples.setdefault(lb, []).append(ex)

        failed_row_count = sum(1 for rf in row_failures if rf["failure_labels"])
        top_failure_types = sorted(
            ((k, v) for k, v in counts.items() if v > 0),
            key=lambda kv: (
                -kv[1],
                FAILURE_LABEL_ORDER.index(kv[0]) if kv[0] in FAILURE_LABEL_ORDER else 99,
            ),
        )

        return {
            "counts": {k: counts[k] for k in FAILURE_LABEL_ORDER if counts[k] > 0},
            "counts_all": dict(counts),
            "examples": {k: v for k, v in examples.items() if v},
            "row_failures": row_failures,
            "top_failure_types": [{"type": t, "count": c} for t, c in top_failure_types],
            "failed_row_count": failed_row_count,
            "critical_count": critical_count,
            "thresholds": {
                "quality": self._q,
                "hallucination": self._hall,
                "low_confidence": self._low_conf,
                "high_confidence_dangerous": self._hi_conf_bad,
            },
        }

    def _classify_row(self, row: dict[str, Any]) -> tuple[list[str], bool]:
        if _coerce_bool(row.get("pipeline_failed")) is True:
            return [], False

        labels: list[str] = []
        judge_failed = _coerce_bool(row.get("judge_failed")) is True

        retrieval_mode = row.get("retrieval_mode")
        exp_docs = _coerce_int(row.get("expected_doc_ids_count"))
        recall_at_k = _coerce_float(row.get("recall_at_k"))

        if retrieval_mode == "none" or (
            exp_docs is not None
            and exp_docs > 0
            and recall_at_k is not None
            and recall_at_k < self._q
        ):
            labels.append("retrieval_failure")

        has_gold = _coerce_bool(row.get("has_expected_answer"))
        if has_gold is None:
            has_gold = False
        answer_f1 = _coerce_float(row.get("answer_f1"))

        groundedness = _coerce_float(row.get("groundedness_score"))
        prompt_doc_id_prec = _coerce_float(row.get("prompt_doc_id_precision"))
        citation_doc_id_rec = _coerce_float(row.get("citation_doc_id_recall"))
        if not judge_failed and groundedness is not None and groundedness < self._q:
            labels.append("grounding_failure")

        if (
            exp_docs is not None
            and exp_docs > 0
            and prompt_doc_id_prec is not None
            and prompt_doc_id_prec < self._q
        ):
            labels.append("context_selection_failure")

        if (
            exp_docs is not None
            and exp_docs > 0
            and citation_doc_id_rec is not None
            and citation_doc_id_rec < self._q
        ):
            labels.append("citation_failure")

        hall_score = _coerce_float(row.get("hallucination_score"))
        hall_flag = _coerce_bool(row.get("has_hallucination"))
        if not judge_failed:
            if (hall_score is not None and hall_score < self._hall) or hall_flag is True:
                labels.append("hallucination")

            rel = _coerce_float(row.get("answer_relevance_score", row.get("answer_relevance")))
            if rel is not None and rel < self._q:
                labels.append("low_relevance")

        conf = _coerce_float(row.get("confidence"))
        if conf is not None and conf < self._low_conf:
            labels.append("low_confidence")

        if (
            has_gold
            and answer_f1 is not None
            and answer_f1 < self._q
            and "grounding_failure" not in labels
        ):
            labels.append("grounding_failure")

        ctx_table = _coerce_bool(row.get("context_uses_table"))
        if ctx_table is None:
            ctx_table = False
        ctx_image = _coerce_bool(row.get("context_uses_image"))
        if ctx_image is None:
            ctx_image = False

        if ctx_table and has_gold and answer_f1 is not None and answer_f1 < self._q:
            labels.append("table_misuse")

        if (
            ctx_image
            and not judge_failed
            and ((hall_score is not None and hall_score < self._hall) or hall_flag is True)
        ):
            labels.append("image_hallucination")

        if judge_failed:
            labels.append("judge_failure")

        ordered = [lb for lb in FAILURE_LABEL_ORDER if lb in labels]

        critical = bool(
            has_gold
            and answer_f1 is not None
            and answer_f1 < self._q
            and conf is not None
            and conf >= self._hi_conf_bad
        )

        return ordered, critical

    def _example_record(
        self,
        row: dict[str, Any],
        labels: list[str],
        critical: bool,
    ) -> dict[str, Any]:
        eid = row.get("entry_id")
        q = row.get("question")
        return {
            "entry_id": eid,
            "question": q if isinstance(q, str) else (str(q) if q is not None else ""),
            "failure_labels": list(labels),
            "failure_critical": bool(critical),
            "answer_preview": row.get("answer_preview")
            if isinstance(row.get("answer_preview"), str)
            else "",
            "recall_at_k": _coerce_float(row.get("recall_at_k")),
            "answer_f1": _coerce_float(row.get("answer_f1")),
            "groundedness_score": _coerce_float(row.get("groundedness_score")),
            "hallucination_score": _coerce_float(row.get("hallucination_score")),
            "answer_relevance_score": _coerce_float(row.get("answer_relevance_score")),
            "confidence": _coerce_float(row.get("confidence")),
            "prompt_doc_id_precision": _coerce_float(row.get("prompt_doc_id_precision")),
            "citation_doc_id_recall": _coerce_float(row.get("citation_doc_id_recall")),
            "context_uses_table": _coerce_bool(row.get("context_uses_table")),
            "context_uses_image": _coerce_bool(row.get("context_uses_image")),
        }
