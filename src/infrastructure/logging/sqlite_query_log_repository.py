"""Compatibility re-exports. Prefer :mod:`src.infrastructure.persistence.sqlite.query_log_repository`."""

from src.infrastructure.persistence.sqlite.query_log_repository import (
    SQLiteQueryLogRepository,
    SQLiteQueryLogRepositoryAdapter,
)

__all__ = ["SQLiteQueryLogRepository", "SQLiteQueryLogRepositoryAdapter"]
