"""Application DTOs for benchmark report exports (Streamlit, API, jobs)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.benchmark_result import BenchmarkResult, BenchmarkRunMetadata


@dataclass(frozen=True)
class BenchmarkExportArtifacts:
    metadata: BenchmarkRunMetadata
    json_bytes: bytes
    json_filename: str
    csv_bytes: bytes
    csv_filename: str
    markdown_bytes: bytes
    markdown_filename: str
    run_id: str | None = None


@dataclass(frozen=True)
class BuildBenchmarkExportCommand:
    """
    Explicit inputs for building JSON/CSV/Markdown benchmark downloads.
    ``result`` is the domain evaluation aggregate; no ad-hoc dict wire format.
    """

    project_id: str
    result: BenchmarkResult
    enable_query_rewrite: bool
    enable_hybrid_retrieval: bool
    generated_at: datetime | str | None = None
