"""Compatibility re-exports. Prefer :mod:`src.infrastructure.persistence.sqlite.qa_dataset_repository`."""

from src.infrastructure.persistence.sqlite.qa_dataset_repository import (
    QADatasetRepository,
    SQLiteQADatasetRepository,
)

__all__ = ["QADatasetRepository", "SQLiteQADatasetRepository"]
