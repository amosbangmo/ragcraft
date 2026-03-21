from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IngestionDiagnostics:
    extraction_ms: float = 0.0
    summarization_ms: float = 0.0
    indexing_ms: float = 0.0
    total_ms: float = 0.0

    extracted_elements: int = 0
    generated_assets: int = 0

    errors: list[str] | None = None

    def to_dict(self) -> dict:
        return {
            "extraction_ms": self.extraction_ms,
            "summarization_ms": self.summarization_ms,
            "indexing_ms": self.indexing_ms,
            "total_ms": self.total_ms,
            "extracted_elements": self.extracted_elements,
            "generated_assets": self.generated_assets,
            "errors": self.errors or [],
        }
