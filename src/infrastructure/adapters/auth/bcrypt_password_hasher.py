"""Bcrypt implementation of :class:`~src.domain.ports.password_hasher_port.PasswordHasherPort`."""

from __future__ import annotations

from src.auth.password_utils import hash_password, verify_password


class BcryptPasswordHasher:
    """Delegates to :mod:`src.auth.password_utils` (shared with legacy Streamlit paths)."""

    def hash_password(self, plaintext: str) -> str:
        return hash_password(plaintext)

    def verify_password(self, plaintext: str, password_hash: str) -> bool:
        return verify_password(plaintext, password_hash)
