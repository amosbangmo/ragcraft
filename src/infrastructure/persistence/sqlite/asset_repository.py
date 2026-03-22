"""Shim: implementation lives in :mod:`src.adapters.sqlite.asset_repository`."""

from src.adapters.sqlite.asset_repository import SQLiteAssetRepository, SQLiteDocStore

__all__ = ["SQLiteAssetRepository", "SQLiteDocStore"]
