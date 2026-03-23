"""Typed rows returned when listing persisted retrieval / query logs (application + HTTP boundary)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RetrievalStrategySnapshot:
    """Subset of retrieval settings stored on a query log row."""

    k: int | None = None
    use_hybrid: bool | None = None
    apply_filters: bool | None = None


@dataclass(frozen=True)
class RetrievalQueryLogRecord:
    """One persisted query / retrieval observation (mirrors HTTP ``RetrievalQueryLogEntry`` fields)."""

    question: str | None = None
    rewritten_query: str | None = None
    project_id: str | None = None
    user_id: str | None = None
    retrieval_mode: str | None = None
    confidence: float | None = None
    timestamp: str | None = None
    selected_doc_ids: list[str] | None = None
    retrieved_doc_ids: list[str] | None = None
    answer: str | None = None
    hybrid_retrieval_enabled: bool | None = None
    query_intent: str | None = None
    retrieval_strategy: RetrievalStrategySnapshot | None = None
    latency_ms: int | None = None
    query_rewrite_ms: int | None = None
    retrieval_ms: int | None = None
    reranking_ms: int | None = None
    prompt_build_ms: int | None = None
    answer_generation_ms: int | None = None
    total_latency_ms: int | None = None
    context_compression_chars_before: int | None = None
    context_compression_chars_after: int | None = None
    context_compression_ratio: float | None = None
    section_expansion_count: int | None = None
    expanded_assets_count: int | None = None
    table_aware_qa_enabled: bool | None = None

    def to_log_entry_dict(self) -> dict[str, Any]:
        """Plain dict for :meth:`~domain.common.shared.query_log_port.QueryLogPersistencePort.log`."""
        out: dict[str, Any] = {}
        if self.question is not None:
            out["question"] = self.question
        if self.rewritten_query is not None:
            out["rewritten_query"] = self.rewritten_query
        if self.project_id is not None:
            out["project_id"] = self.project_id
        if self.user_id is not None:
            out["user_id"] = self.user_id
        if self.retrieval_mode is not None:
            out["retrieval_mode"] = self.retrieval_mode
        if self.confidence is not None:
            out["confidence"] = self.confidence
        if self.timestamp is not None:
            out["timestamp"] = self.timestamp
        if self.selected_doc_ids is not None:
            out["selected_doc_ids"] = list(self.selected_doc_ids)
        if self.retrieved_doc_ids is not None:
            out["retrieved_doc_ids"] = list(self.retrieved_doc_ids)
        if self.answer is not None:
            out["answer"] = self.answer
        if self.hybrid_retrieval_enabled is not None:
            out["hybrid_retrieval_enabled"] = self.hybrid_retrieval_enabled
        if self.query_intent is not None:
            out["query_intent"] = self.query_intent
        if self.retrieval_strategy is not None:
            rs = self.retrieval_strategy
            strat: dict[str, Any] = {}
            if rs.k is not None:
                strat["k"] = rs.k
            if rs.use_hybrid is not None:
                strat["use_hybrid"] = rs.use_hybrid
            if rs.apply_filters is not None:
                strat["apply_filters"] = rs.apply_filters
            if strat:
                out["retrieval_strategy"] = strat
        for key in (
            "latency_ms",
            "query_rewrite_ms",
            "retrieval_ms",
            "reranking_ms",
            "prompt_build_ms",
            "answer_generation_ms",
            "total_latency_ms",
            "context_compression_chars_before",
            "context_compression_chars_after",
            "context_compression_ratio",
            "section_expansion_count",
            "expanded_assets_count",
        ):
            val = getattr(self, key)
            if val is not None:
                out[key] = val
        if self.table_aware_qa_enabled is not None:
            out["table_aware_qa_enabled"] = self.table_aware_qa_enabled
        return out


def retrieval_query_log_record_from_plain_mapping(d: Mapping[str, Any]) -> RetrievalQueryLogRecord:
    """Build a record from a SQLite row dict or legacy JSON line (same keys as historical dict contract)."""
    rs_raw = d.get("retrieval_strategy")
    rs: RetrievalStrategySnapshot | None = None
    if isinstance(rs_raw, Mapping) and rs_raw:
        k_raw = rs_raw.get("k")
        k_val: int | None = None
        if k_raw is not None:
            try:
                k_val = int(k_raw)
            except (TypeError, ValueError):
                k_val = None
        uh_val: bool | None = None
        if "use_hybrid" in rs_raw:
            uh_val = bool(rs_raw.get("use_hybrid"))
        af_val: bool | None = None
        if "apply_filters" in rs_raw:
            af_val = bool(rs_raw.get("apply_filters"))
        if k_val is not None or uh_val is not None or af_val is not None:
            rs = RetrievalStrategySnapshot(k=k_val, use_hybrid=uh_val, apply_filters=af_val)

    def _opt_int(key: str) -> int | None:
        v = d.get(key)
        if v is None:
            return None
        try:
            return int(round(float(v)))
        except (TypeError, ValueError):
            return None

    def _opt_float(key: str) -> float | None:
        v = d.get(key)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    sel = d.get("selected_doc_ids")
    selected_doc_ids = [str(x) for x in sel] if isinstance(sel, list) else None
    ret = d.get("retrieved_doc_ids")
    retrieved_doc_ids = [str(x) for x in ret] if isinstance(ret, list) else None

    return RetrievalQueryLogRecord(
        question=None if d.get("question") is None else str(d["question"]),
        rewritten_query=None if d.get("rewritten_query") is None else str(d["rewritten_query"]),
        project_id=None if d.get("project_id") is None else str(d["project_id"]),
        user_id=None if d.get("user_id") is None else str(d["user_id"]),
        retrieval_mode=None if d.get("retrieval_mode") is None else str(d["retrieval_mode"]),
        confidence=_opt_float("confidence"),
        timestamp=None if d.get("timestamp") is None else str(d["timestamp"]),
        selected_doc_ids=selected_doc_ids,
        retrieved_doc_ids=retrieved_doc_ids,
        answer=None if d.get("answer") is None else str(d["answer"]),
        hybrid_retrieval_enabled=bool(d["hybrid_retrieval_enabled"])
        if d.get("hybrid_retrieval_enabled") is not None
        else None,
        query_intent=None if d.get("query_intent") is None else str(d["query_intent"]),
        retrieval_strategy=rs,
        latency_ms=_opt_int("latency_ms"),
        query_rewrite_ms=_opt_int("query_rewrite_ms"),
        retrieval_ms=_opt_int("retrieval_ms"),
        reranking_ms=_opt_int("reranking_ms"),
        prompt_build_ms=_opt_int("prompt_build_ms"),
        answer_generation_ms=_opt_int("answer_generation_ms"),
        total_latency_ms=_opt_int("total_latency_ms"),
        context_compression_chars_before=_opt_int("context_compression_chars_before"),
        context_compression_chars_after=_opt_int("context_compression_chars_after"),
        context_compression_ratio=_opt_float("context_compression_ratio"),
        section_expansion_count=_opt_int("section_expansion_count"),
        expanded_assets_count=_opt_int("expanded_assets_count"),
        table_aware_qa_enabled=bool(d["table_aware_qa_enabled"])
        if d.get("table_aware_qa_enabled") is not None
        else None,
    )
