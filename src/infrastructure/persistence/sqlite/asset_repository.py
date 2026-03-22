"""Shim: implementation lives in :mod:`src.infrastructure.adapters.sqlite.asset_repository`."""

from src.infrastructure.adapters.sqlite.asset_repository import SQLiteAssetRepository, SQLiteDocStore

__all__ = ["SQLiteAssetRepository", "SQLiteDocStore"]
