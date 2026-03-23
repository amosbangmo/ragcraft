from dataclasses import dataclass, field
from typing import Any

from src.domain.pipeline_latency import PipelineLatency


@dataclass
class RAGResponse:
    question: str
    answer: str
    source_documents: list[Any] = field(default_factory=list)
    raw_assets: list[Any] = field(default_factory=list)
    prompt_sources: list[Any] = field(default_factory=list)
    confidence: float = 0.0
    latency: PipelineLatency | None = None
