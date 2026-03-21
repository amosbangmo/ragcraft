"""Compatibility re-exports. Prefer :mod:`src.infrastructure.persistence.sqlite.asset_repository`."""

from src.infrastructure.persistence.sqlite.asset_repository import SQLiteAssetRepository, SQLiteDocStore

__all__ = ["SQLiteAssetRepository", "SQLiteDocStore"]
