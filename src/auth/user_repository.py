"""Shim: SQLite implementation is :class:`~src.adapters.sqlite.user_repository.SqliteUserRepository`."""

from src.adapters.sqlite.user_repository import SqliteUserRepository

UserRepository = SqliteUserRepository

__all__ = ["SqliteUserRepository", "UserRepository"]
