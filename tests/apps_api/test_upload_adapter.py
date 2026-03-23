"""Multipart upload transport: chunked read and size cap."""

from __future__ import annotations

import asyncio
import io

import pytest
from fastapi import UploadFile

from apps.api.upload_adapter import (
    StarletteUploadTooLargeError,
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
