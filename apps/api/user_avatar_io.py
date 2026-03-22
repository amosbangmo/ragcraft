"""Avatar file validation and storage under ``<data_root>/users/<user_id>/profile/`` (API layer)."""

from __future__ import annotations

from pathlib import Path

_MAX_AVATAR_BYTES = 2 * 1024 * 1024
_ALLOWED_AVATAR_EXT = frozenset({".png", ".jpg", ".jpeg", ".webp"})

# Normalized MIME primary types we accept (plus application/octet-stream from some clients).
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
    """Reject a declared Content-Type that clearly conflicts with the file extension."""
    ct = _normalize_mime(content_type)
    if ct is None or ct == "application/octet-stream":
        return
    allowed = _SUFFIX_TO_MIMES.get(suffix, frozenset())
    if ct not in allowed:
        raise ValueError("Content-Type does not match the uploaded image format.")


def validate_avatar_magic(suffix: str, raw: bytes) -> None:
    """Ensure bytes look like the claimed image format (not merely a renamed file)."""
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


def write_avatar_bytes(
    *,
    data_root: Path,
    user_id: str,
    suffix: str,
    raw: bytes,
    content_type: str | None = None,
) -> Path:
    if len(raw) > _MAX_AVATAR_BYTES:
        raise ValueError("Avatar exceeds maximum size.")
    validate_avatar_mime(suffix, content_type)
    validate_avatar_magic(suffix, raw)
    avatar_dir = user_tree_root(data_root, user_id) / "profile"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    dest = (avatar_dir / f"avatar{suffix}").resolve()
    for existing in avatar_dir.glob("avatar.*"):
        try:
            if existing.resolve() != dest:
                existing.unlink(missing_ok=True)
        except OSError:
            continue
    dest.write_bytes(raw)
    return dest


def safe_remove_stored_avatar_file(*, data_root: Path, user_id: str, avatar_path_str: str | None) -> None:
    """
    Delete a stored avatar only if it resolves to a file under this user's data tree (no path escape).
    """
    if not avatar_path_str or not str(avatar_path_str).strip():
        return
    root = user_tree_root(data_root, user_id)
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
