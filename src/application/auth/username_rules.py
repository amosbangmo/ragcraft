"""Shared username format rules for registration and profile updates."""

from __future__ import annotations

import re

USERNAME_PATTERN = re.compile(r"[a-z0-9._-]{3,30}")


def normalized_username(raw: str) -> str:
    return raw.strip().lower()


def is_valid_username(normalized: str) -> bool:
    return bool(normalized) and bool(USERNAME_PATTERN.fullmatch(normalized))
