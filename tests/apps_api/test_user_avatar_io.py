"""Avatar path safety and size limits (filesystem adapter)."""

from __future__ import annotations

import pytest

import src.infrastructure.adapters.filesystem.file_avatar_storage as fas
from src.infrastructure.adapters.filesystem.file_avatar_storage import FileAvatarStorage


def test_safe_remove_ignores_path_outside_user_tree(tmp_path) -> None:
    victim = tmp_path / "secret.txt"
    victim.write_text("keep")
    data_root = tmp_path / "data"
    (data_root / "users" / "u1").mkdir(parents=True)
    storage = FileAvatarStorage(data_root=data_root)
    storage.remove_avatar_if_stored("u1", str(victim))
    assert victim.read_text() == "keep"


def test_safe_remove_deletes_file_under_profile(tmp_path) -> None:
    data_root = tmp_path / "data"
    profile = data_root / "users" / "u1" / "profile"
    profile.mkdir(parents=True)
    img = profile / "avatar.png"
    img.write_bytes(b"x")
    storage = FileAvatarStorage(data_root=data_root)
    storage.remove_avatar_if_stored("u1", str(img))
    assert not img.exists()


def test_avatar_suffix_rejects_blank_filename() -> None:
    with pytest.raises(ValueError, match="choose"):
        fas.avatar_suffix_from_upload_filename(None)
    with pytest.raises(ValueError, match="choose"):
        fas.avatar_suffix_from_upload_filename("   ")


def test_save_avatar_respects_max_size(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fas, "_MAX_AVATAR_BYTES", 8)
    data_root = tmp_path / "data"
    storage = FileAvatarStorage(data_root=data_root)
    with pytest.raises(ValueError, match="maximum size"):
        storage.save_avatar(
            user_id="u1",
            upload_filename="x.png",
            raw=b"123456789",
            content_type="image/png",
        )


def test_validate_avatar_mime_rejects_mismatch() -> None:
    with pytest.raises(ValueError, match="Content-Type"):
        fas.validate_avatar_mime(".png", "image/jpeg")


def test_validate_avatar_magic_requires_real_header(tmp_path) -> None:
    data_root = tmp_path / "data"
    storage = FileAvatarStorage(data_root=data_root)
    with pytest.raises(ValueError, match="not a valid image"):
        storage.save_avatar(
            user_id="u1",
            upload_filename="x.png",
            raw=b"fake",
            content_type="image/png",
        )
