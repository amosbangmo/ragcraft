"""Application validation for bounded avatar uploads."""

from __future__ import annotations

from dataclasses import replace

import pytest

import application.policies.avatar_upload_policy as avatar_upload_policy
import infrastructure.config.config as cfg
from application.policies.avatar_upload_policy import validate_buffered_avatar_upload
from domain.projects.buffered_document_upload import BufferedDocumentUpload


def test_validate_avatar_rejects_empty() -> None:
    up = BufferedDocumentUpload(source_filename="x.png", body=b"")
    with pytest.raises(ValueError, match="empty"):
        validate_buffered_avatar_upload(up)


def test_validate_avatar_rejects_over_config_max(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        avatar_upload_policy,
        "USER_PROFILE_UPLOAD_CONFIG",
        replace(cfg.USER_PROFILE_UPLOAD_CONFIG, max_avatar_bytes=3),
    )
    up = BufferedDocumentUpload(source_filename="x.png", body=b"1234")
    with pytest.raises(ValueError, match="exceeds"):
        validate_buffered_avatar_upload(up)


def test_validate_avatar_accepts_within_limit() -> None:
    up = BufferedDocumentUpload(source_filename="x.png", body=b"12")
    assert validate_buffered_avatar_upload(up) is up
