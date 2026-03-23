"""Technical port for password hashing and verification (bcrypt or future algorithms)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PasswordHasherPort(Protocol):
    def hash_password(self, plaintext: str) -> str: ...

    def verify_password(self, plaintext: str, password_hash: str) -> bool: ...
