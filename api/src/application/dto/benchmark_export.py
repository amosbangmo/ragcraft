"""Application DTOs for benchmark report exports (Streamlit, API, jobs)."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from domain.evaluation.benchmark_result import BenchmarkResult, BenchmarkRunMetadata


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

    def to_http_bundle_dict(self) -> dict[str, Any]:
        """JSON-safe body for POST ``export_format=all`` (base64 file payloads + metadata)."""
        return {
            "metadata": self.metadata.to_dict(),
            "json_base64": base64.standard_b64encode(self.json_bytes).decode("ascii"),
            "json_filename": self.json_filename,
            "csv_base64": base64.standard_b64encode(self.csv_bytes).decode("ascii"),
            "csv_filename": self.csv_filename,
            "markdown_base64": base64.standard_b64encode(self.markdown_bytes).decode("ascii"),
            "markdown_filename": self.markdown_filename,
            "run_id": self.run_id,
        }


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
