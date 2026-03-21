from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class PipelineLatency:
    query_rewrite_ms: float = 0.0
    retrieval_ms: float = 0.0
    reranking_ms: float = 0.0
    prompt_build_ms: float = 0.0
    answer_generation_ms: float = 0.0
    total_ms: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "query_rewrite_ms": self.query_rewrite_ms,
            "retrieval_ms": self.retrieval_ms,
            "reranking_ms": self.reranking_ms,
            "prompt_build_ms": self.prompt_build_ms,
            "answer_generation_ms": self.answer_generation_ms,
            "total_ms": self.total_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PipelineLatency:
        if not data:
            return cls()
        return cls(
            query_rewrite_ms=float(data.get("query_rewrite_ms", 0.0)),
            retrieval_ms=float(data.get("retrieval_ms", 0.0)),
            reranking_ms=float(data.get("reranking_ms", 0.0)),
            prompt_build_ms=float(data.get("prompt_build_ms", 0.0)),
            answer_generation_ms=float(data.get("answer_generation_ms", 0.0)),
            total_ms=float(data.get("total_ms", 0.0)),
        )


def merge_with_answer_stage(
    pipeline_partial: dict[str, Any] | None,
    *,
    answer_generation_ms: float,
    total_ms: float,
) -> PipelineLatency:
    base = PipelineLatency.from_dict(pipeline_partial)
    return replace(
        base,
        answer_generation_ms=answer_generation_ms,
        total_ms=total_ms,
    )
