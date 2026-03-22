"""Unit tests for avatar path safety and size limits."""

from __future__ import annotations

import pytest

from apps.api import user_avatar_io as av


def test_safe_remove_ignores_path_outside_user_tree(tmp_path) -> None:
    victim = tmp_path / "secret.txt"
    victim.write_text("keep")
    data_root = tmp_path / "data"
    (data_root / "users" / "u1").mkdir(parents=True)
    av.safe_remove_stored_avatar_file(
        data_root=data_root,
        user_id="u1",
        avatar_path_str=str(victim),
    )
    assert victim.read_text() == "keep"


def test_safe_remove_deletes_file_under_profile(tmp_path) -> None:
    data_root = tmp_path / "data"
    profile = data_root / "users" / "u1" / "profile"
    profile.mkdir(parents=True)
    img = profile / "avatar.png"
    img.write_bytes(b"x")
    av.safe_remove_stored_avatar_file(
        data_root=data_root,
        user_id="u1",
        avatar_path_str=str(img),
    )
    assert not img.exists()


def test_avatar_suffix_rejects_blank_filename() -> None:
    with pytest.raises(ValueError, match="choose"):
        av.avatar_suffix_from_upload_filename(None)
    with pytest.raises(ValueError, match="choose"):
        av.avatar_suffix_from_upload_filename("   ")


def test_write_avatar_respects_max_size(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(av, "_MAX_AVATAR_BYTES", 8)
    data_root = tmp_path / "data"
    with pytest.raises(ValueError, match="maximum size"):
        av.write_avatar_bytes(
            data_root=data_root,
            user_id="u1",
            suffix=".png",
            raw=b"123456789",
        )
