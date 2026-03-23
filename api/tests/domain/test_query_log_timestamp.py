"""Tests for :mod:`domain.rag.query_log_timestamp`."""

from __future__ import annotations

from datetime import UTC

import pytest

from domain.rag.query_log_timestamp import parse_query_log_timestamp


def test_parse_query_log_timestamp_none_or_empty() -> None:
    assert parse_query_log_timestamp({}) is None
    assert parse_query_log_timestamp({"timestamp": None}) is None
    assert parse_query_log_timestamp({"timestamp": ""}) is None
    assert parse_query_log_timestamp({"timestamp": "   "}) is None


def test_parse_query_log_timestamp_invalid_type() -> None:
    assert parse_query_log_timestamp({"timestamp": 123}) is None


def test_parse_query_log_timestamp_z_suffix() -> None:
    dt = parse_query_log_timestamp({"timestamp": "2024-01-15T12:30:00Z"})
    assert dt is not None
    assert dt.tzinfo == UTC
    assert dt.year == 2024 and dt.month == 1 and dt.day == 15


def test_parse_query_log_timestamp_naive_becomes_utc() -> None:
    dt = parse_query_log_timestamp({"timestamp": "2024-06-01T08:00:00"})
    assert dt is not None
    assert dt.tzinfo == UTC


def test_parse_query_log_timestamp_invalid_string() -> None:
    assert parse_query_log_timestamp({"timestamp": "not-a-date"}) is None


@pytest.mark.parametrize(
    "raw,expected_hour",
    [
        ("2024-03-20T15:00:00+05:00", 10),  # 15:00+5 -> 10:00 UTC
    ],
)
def test_parse_query_log_timestamp_offset_normalized(raw: str, expected_hour: int) -> None:
    dt = parse_query_log_timestamp({"timestamp": raw})
    assert dt is not None
    assert dt.astimezone(UTC).hour == expected_hour
