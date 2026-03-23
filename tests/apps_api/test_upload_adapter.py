"""Multipart upload transport: chunked read and size cap."""

from __future__ import annotations

import asyncio
import io
from dataclasses import replace

import pytest
from fastapi import UploadFile

import src.core.config as cfg
from apps.api.upload_adapter import (
    StarletteUploadTooLargeError,
    read_buffered_avatar_upload,
    read_buffered_document_upload,
)


def test_read_buffered_upload_happy_path() -> None:
    uf = UploadFile(filename="doc.txt", file=io.BytesIO(b"hello"))
    up = asyncio.run(read_buffered_document_upload(uf, max_bytes=100))
    assert up.source_filename == "doc.txt"
    assert up.body == b"hello"
    assert up.declared_media_type is None


def test_read_buffered_upload_rejects_over_max() -> None:
    uf = UploadFile(filename="big.bin", file=io.BytesIO(b"x" * 20))
    with pytest.raises(StarletteUploadTooLargeError):
        asyncio.run(read_buffered_document_upload(uf, max_bytes=10))


def test_read_buffered_avatar_upload_happy_path() -> None:
    uf = UploadFile(filename="a.png", file=io.BytesIO(b"\x89PNG\r\n\x1a\n"))
    up = asyncio.run(read_buffered_avatar_upload(uf, default_name="avatar"))
    assert up.source_filename == "a.png"
    assert up.body.startswith(b"\x89PNG")


def test_read_buffered_avatar_upload_rejects_over_default_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.api.upload_adapter.USER_PROFILE_UPLOAD_CONFIG",
        replace(cfg.USER_PROFILE_UPLOAD_CONFIG, max_avatar_bytes=5),
    )
    uf = UploadFile(filename="x.png", file=io.BytesIO(b"123456"))
    with pytest.raises(StarletteUploadTooLargeError):
        asyncio.run(read_buffered_avatar_upload(uf))
