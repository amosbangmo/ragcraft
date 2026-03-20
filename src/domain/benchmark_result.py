from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkRow:
    """
    Structured per-entry benchmark result.

    The ``data`` payload intentionally stays flexible so the evaluation layer can
    evolve incrementally without forcing a broad refactor across the UI.
    """

    entry_id: int
    question: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "question": self.question,
            **dict(self.data),
        }


@dataclass(frozen=True)
class BenchmarkSummary:
    """
    Structured benchmark summary.

    As with ``BenchmarkRow``, the payload remains flexible on purpose. This lets
    the project move from dict-based evaluation to typed results without forcing
    every future metric to become a top-level dataclass field immediately.
    """

    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.data)


@dataclass(frozen=True)
class BenchmarkResult:
    """
    Full benchmark result returned by the evaluation layer.

    This becomes the application contract between:
    - service layer
    - app facade
    - Streamlit UI
    - future export/report layers
    """

    summary: BenchmarkSummary
    rows: list[BenchmarkRow] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "rows": [row.to_dict() for row in self.rows],
        }
