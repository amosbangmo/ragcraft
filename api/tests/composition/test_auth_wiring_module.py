"""Lightweight composition package smoke (no full backend graph)."""

from __future__ import annotations


def test_auth_wiring_module_is_importable() -> None:
    import composition.auth_wiring as auth_wiring

    assert "Auth" in (auth_wiring.__doc__ or "")
