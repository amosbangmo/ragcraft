"""
Filesystem avatar storage under ``<data_root>/users/<user_id>/``.

Moved from ``apps.api.user_avatar_io`` so application use cases depend on
:class:`~src.domain.ports.avatar_storage_port.AvatarStoragePort` only.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from src.core.config import USER_PROFILE_UPLOAD_CONFIG
from src.core.paths import get_data_root

_ALLOWED_AVATAR_EXT = frozenset({".png", ".jpg", ".jpeg", ".webp"})
_SUFFIX_TO_MIMES: dict[str, frozenset[str]] = {
    ".png": frozenset({"image/png"}),
    ".jpg": frozenset({"image/jpeg", "image/jpg"}),
    ".jpeg": frozenset({"image/jpeg", "image/jpg"}),
    ".webp": frozenset({"image/webp"}),
}


def _normalize_mime(content_type: str | None) -> str | None:
    if content_type is None or not str(content_type).strip():
        return None
    return str(content_type).split(";", 1)[0].strip().lower()


def validate_avatar_mime(suffix: str, content_type: str | None) -> None:
    ct = _normalize_mime(content_type)
    if ct is None or ct == "application/octet-stream":
        return
    allowed = _SUFFIX_TO_MIMES.get(suffix, frozenset())
    if ct not in allowed:
        raise ValueError("Content-Type does not match the uploaded image format.")


def validate_avatar_magic(suffix: str, raw: bytes) -> None:
    if suffix == ".png":
        ok = raw.startswith(b"\x89PNG\r\n\x1a\n")
    elif suffix in (".jpg", ".jpeg"):
        ok = len(raw) >= 3 and raw[:3] == b"\xff\xd8\xff"
    elif suffix == ".webp":
        ok = len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
    else:
        ok = False
    if not ok:
        raise ValueError("File content is not a valid image for the chosen format.")


def user_tree_root(data_root: Path, user_id: str) -> Path:
    return (data_root / "users" / user_id).resolve()


def avatar_suffix_from_upload_filename(filename: str | None) -> str:
    if filename is None or not str(filename).strip():
        raise ValueError("Please choose an image.")
    suffix = Path(str(filename).strip()).suffix.lower()
    if suffix not in _ALLOWED_AVATAR_EXT:
        raise ValueError("Unsupported format. Use PNG, JPG, JPEG, or WEBP.")
    return suffix


class FileAvatarStorage:
    """On-disk avatars and safe removal within the user's data subtree."""

    def __init__(self, *, data_root: Path | None = None) -> None:
        self._data_root_override = data_root

    def _data_root(self) -> Path:
        return self._data_root_override if self._data_root_override is not None else get_data_root()

    def save_avatar(
        self,
        *,
        user_id: str,
        upload_filename: str | None,
        raw: bytes,
        content_type: str | None,
    ) -> str:
        suffix = avatar_suffix_from_upload_filename(upload_filename)
        if len(raw) > USER_PROFILE_UPLOAD_CONFIG.max_avatar_bytes:
            raise ValueError("Avatar exceeds maximum size.")
        validate_avatar_mime(suffix, content_type)
        validate_avatar_magic(suffix, raw)
        root = self._data_root()
        avatar_dir = user_tree_root(root, user_id) / "profile"
        avatar_dir.mkdir(parents=True, exist_ok=True)
        dest = (avatar_dir / f"avatar{suffix}").resolve()
        for existing in avatar_dir.glob("avatar.*"):
            try:
                if existing.resolve() != dest:
                    existing.unlink(missing_ok=True)
            except OSError:
                continue
        dest.write_bytes(raw)
        return str(dest)

    def remove_avatar_if_stored(self, user_id: str, avatar_path_str: str | None) -> None:
        if not avatar_path_str or not str(avatar_path_str).strip():
            return
        root = user_tree_root(self._data_root(), user_id)
        try:
            candidate = Path(str(avatar_path_str).strip()).expanduser().resolve()
        except (OSError, RuntimeError):
            return
        try:
            candidate.relative_to(root)
        except ValueError:
            return
        if candidate.is_file():
            candidate.unlink(missing_ok=True)

    def delete_user_data_tree(self, user_id: str) -> None:
        tree = self._data_root() / "users" / user_id
        if tree.exists():
            shutil.rmtree(tree, ignore_errors=True)
