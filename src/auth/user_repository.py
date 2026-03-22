"""Shim: SQLite implementation is :class:`~src.infrastructure.adapters.sqlite.user_repository.SqliteUserRepository`."""

from src.infrastructure.adapters.sqlite.user_repository import SqliteUserRepository

UserRepository = SqliteUserRepository

__all__ = ["SqliteUserRepository", "UserRepository"]
