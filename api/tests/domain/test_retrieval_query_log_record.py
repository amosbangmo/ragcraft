from __future__ import annotations

from domain.common.retrieval_query_log_record import (
    RetrievalQueryLogRecord,
    RetrievalStrategySnapshot,
    retrieval_query_log_record_from_plain_mapping,
)


def test_to_log_entry_dict_minimal() -> None:
    r = RetrievalQueryLogRecord(question="hi")
    d = r.to_log_entry_dict()
    assert d == {"question": "hi"}


def test_to_log_entry_dict_full_strategy_and_latencies() -> None:
    r = RetrievalQueryLogRecord(
        question="q",
        rewritten_query="rq",
        project_id="p",
        user_id="u",
        retrieval_mode="hybrid",
        confidence=0.5,
        timestamp="t",
        selected_doc_ids=["a"],
        retrieved_doc_ids=["b"],
        answer="ans",
        hybrid_retrieval_enabled=True,
        query_intent="factual",
        retrieval_strategy=RetrievalStrategySnapshot(k=3, use_hybrid=True, apply_filters=False),
        latency_ms=10,
        query_rewrite_ms=1,
        retrieval_ms=2,
        reranking_ms=3,
        prompt_build_ms=4,
        answer_generation_ms=5,
        total_latency_ms=15,
        context_compression_chars_before=100,
        context_compression_chars_after=50,
        context_compression_ratio=0.5,
        section_expansion_count=2,
        expanded_assets_count=3,
        table_aware_qa_enabled=True,
    )
    d = r.to_log_entry_dict()
    assert d["retrieval_strategy"] == {
        "k": 3,
        "use_hybrid": True,
        "apply_filters": False,
    }
    assert d["latency_ms"] == 10
    assert d["table_aware_qa_enabled"] is True


def test_from_plain_mapping_strategy_invalid_k() -> None:
    r = retrieval_query_log_record_from_plain_mapping(
        {
            "question": "x",
            "retrieval_strategy": {"k": "nope", "use_hybrid": True},
        }
    )
    assert r.retrieval_strategy is not None
    assert r.retrieval_strategy.k is None
    assert r.retrieval_strategy.use_hybrid is True


def test_from_plain_mapping_opt_int_float_invalid() -> None:
    r = retrieval_query_log_record_from_plain_mapping(
        {
            "confidence": "x",
            "latency_ms": "nan",
            "context_compression_ratio": [],
        }
    )
    assert r.confidence is None
    assert r.latency_ms is None
    assert r.context_compression_ratio is None


def test_from_plain_mapping_doc_id_lists() -> None:
    r = retrieval_query_log_record_from_plain_mapping(
        {
            "selected_doc_ids": [1, 2],
            "retrieved_doc_ids": "bad",
        }
    )
    assert r.selected_doc_ids == ["1", "2"]
    assert r.retrieved_doc_ids is None
