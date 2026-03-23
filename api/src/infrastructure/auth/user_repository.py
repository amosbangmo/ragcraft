"""Shim: SQLite implementation is :class:`~infrastructure.persistence.sqlite.user_repository.SqliteUserRepository`."""

from infrastructure.persistence.sqlite.user_repository import SqliteUserRepository

UserRepository = SqliteUserRepository

__all__ = ["SqliteUserRepository", "UserRepository"]
