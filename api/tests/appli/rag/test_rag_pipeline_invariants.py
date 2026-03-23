"""
Explicit structural invariants for the RAG pipeline (inspect vs ask, modes, latency, logs).

Fails fast when wire shapes drift between ``POST /chat/pipeline/inspect`` and ``POST /chat/ask``.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from application.use_cases.chat.ask_question import AskQuestionUseCase
from application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
from domain.projects.project import Project
from domain.rag.pipeline_latency import PipelineLatency, merge_with_answer_stage
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.rag.rag_response import RAGResponse


def _latency_keys() -> frozenset[str]:
    return frozenset(PipelineLatency().to_dict().keys())


def test_pipeline_latency_wire_roundtrip_invariant() -> None:
    d = {
        "query_rewrite_ms": 1.0,
        "retrieval_ms": 2.0,
        "reranking_ms": 3.0,
        "prompt_build_ms": 4.0,
        "answer_generation_ms": 5.0,
        "total_ms": 15.0,
    }
    pl = PipelineLatency.from_dict(d)
    assert pl.to_dict() == d


def test_merge_with_answer_stage_preserves_inspect_stages() -> None:
    partial = PipelineLatency(
        query_rewrite_ms=1.0,
        retrieval_ms=2.0,
        reranking_ms=3.0,
        prompt_build_ms=4.0,
        answer_generation_ms=0.0,
        total_ms=10.0,
    )
    merged = merge_with_answer_stage(
        partial, answer_generation_ms=40.0, total_ms=50.0
    )
    assert merged.query_rewrite_ms == 1.0
    assert merged.retrieval_ms == 2.0
    assert merged.answer_generation_ms == 40.0
    assert merged.total_ms == 50.0


def test_inspect_pipeline_to_dict_includes_latency_and_mode_flags() -> None:
    p = Project(user_id="u", project_id="p")
    pipeline = PipelineBuildResult(
        question="q",
        rewritten_question="rq",
        retrieval_mode="hybrid",
        query_rewrite_enabled=True,
        hybrid_retrieval_enabled=True,
    )
    d = pipeline.to_dict()
    assert d["retrieval_mode"] == "hybrid"
    assert d["query_rewrite_enabled"] is True
    assert d["hybrid_retrieval_enabled"] is True
    assert "latency" in d
    assert frozenset((d.get("latency") or {}).keys()) <= _latency_keys()


@pytest.mark.parametrize(
    ("mode", "hybrid"),
    [("faiss", False), ("hybrid", True)],
)
def test_faiss_vs_hybrid_mode_strings(mode: str, hybrid: bool) -> None:
    pl = PipelineBuildResult(retrieval_mode=mode, hybrid_retrieval_enabled=hybrid)
    d = pl.to_dict()
    assert d["retrieval_mode"] == mode
    assert d["hybrid_retrieval_enabled"] is hybrid


def test_ask_merges_latency_like_inspect_plus_answer_stage() -> None:
    project = Project(user_id="u", project_id="p")
    pipeline = PipelineBuildResult(
        latency=PipelineLatency(
            query_rewrite_ms=1.0,
            retrieval_ms=2.0,
            reranking_ms=3.0,
            prompt_build_ms=4.0,
            answer_generation_ms=0.0,
            total_ms=10.0,
        )
    )

    generation = MagicMock()
    generation.generate_answer.return_value = "answer text"

    retrieval = MagicMock()
    retrieval.execute.return_value = pipeline
    ask = AskQuestionUseCase(
        retrieval=retrieval,
        generation=generation,
        query_log=None,
    )
    out = ask.execute(project, "q", [])
    assert isinstance(out, RAGResponse)
    assert out.latency is not None
    assert out.latency.answer_generation_ms >= 0.0
    assert out.latency.total_ms >= out.latency.answer_generation_ms
    assert out.latency.retrieval_ms == 2.0


def test_inspect_does_not_emit_answer_stage_latency_in_pipeline_object() -> None:
    project = Project(user_id="u", project_id="p")
    built = PipelineBuildResult(
        latency=PipelineLatency(answer_generation_ms=0.0, total_ms=9.0)
    )
    retrieval = MagicMock()
    retrieval.execute.return_value = built
    inspect = InspectRagPipelineUseCase(retrieval=retrieval)
    result = inspect.execute(project, "q", [])
    assert result is not None
    assert result.latency.answer_generation_ms == 0.0
