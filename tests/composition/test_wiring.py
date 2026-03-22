from __future__ import annotations

from src.composition.wiring import process_scoped_chain_invalidate_key


def test_process_scoped_chain_invalidate_key_returns_callable() -> None:
    drop = process_scoped_chain_invalidate_key()
    assert callable(drop)
    drop("any-project-id")  # idempotent on empty cache
