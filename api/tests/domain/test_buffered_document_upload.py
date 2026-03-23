"""Tests for :mod:`domain.projects.buffered_document_upload`."""

from __future__ import annotations

import pytest

from domain.projects.buffered_document_upload import BufferedDocumentUpload


def test_buffered_document_upload_name_and_buffer() -> None:
    u = BufferedDocumentUpload(source_filename="doc.pdf", body=b"hello")
    assert u.name == "doc.pdf"
    assert bytes(u.getbuffer()) == b"hello"
    assert u.size_bytes == 5


def test_from_duck_typed_minimal() -> None:
    class Fake:
        name = "a.txt"
        type = "text/plain"

        def getbuffer(self):
            return memoryview(b"abc")

    u = BufferedDocumentUpload.from_duck_typed(Fake())
    assert u.source_filename == "a.txt"
    assert u.body == b"abc"
    assert u.declared_media_type == "text/plain"


def test_from_duck_typed_default_name() -> None:
    class Fake:
        def getbuffer(self):
            return memoryview(b"x")

    u = BufferedDocumentUpload.from_duck_typed(Fake(), default_name="fallback")
    assert u.source_filename == "fallback"


def test_from_duck_typed_missing_getbuffer() -> None:
    class Bad:
        name = "nope"

    with pytest.raises(TypeError, match="getbuffer"):
        BufferedDocumentUpload.from_duck_typed(Bad())


def test_from_duck_typed_coerces_non_str_media_type() -> None:
    class Fake:
        name = "f.bin"
        type = 123

        def getbuffer(self):
            return memoryview(b"")

    u = BufferedDocumentUpload.from_duck_typed(Fake())
    assert u.declared_media_type == "123"
