"""Tests for coercion helpers in :mod:`domain.evaluation.benchmark_failure_analysis`."""

from __future__ import annotations

import domain.evaluation.benchmark_failure_analysis as bfa


def test_coerce_float_rejects_bool() -> None:
    assert bfa._coerce_float(True) is None
    assert bfa._coerce_float(False) is None


def test_coerce_float_valid() -> None:
    assert bfa._coerce_float("3.5") == 3.5
    assert bfa._coerce_float(2) == 2.0


def test_coerce_bool_from_string() -> None:
    assert bfa._coerce_bool(" YES ") is True
    assert bfa._coerce_bool("no") is False
    assert bfa._coerce_bool("maybe") is None


def test_coerce_int_bool_becomes_int() -> None:
    assert bfa._coerce_int(True) == 1
