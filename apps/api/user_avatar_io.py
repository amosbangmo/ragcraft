"""Avatar file validation and storage under ``<data_root>/users/<user_id>/profile/`` (API layer)."""

from __future__ import annotations

from pathlib import Path

_MAX_AVATAR_BYTES = 2 * 1024 * 1024
_ALLOWED_AVATAR_EXT = frozenset({".png", ".jpg", ".jpeg", ".webp"})


def user_tree_root(data_root: Path, user_id: str) -> Path:
    return (data_root / "users" / user_id).resolve()


def avatar_suffix_from_upload_filename(filename: str | None) -> str:
    if filename is None or not str(filename).strip():
        raise ValueError("Please choose an image.")
    suffix = Path(str(filename).strip()).suffix.lower()
    if suffix not in _ALLOWED_AVATAR_EXT:
        raise ValueError("Unsupported format. Use PNG, JPG, JPEG, or WEBP.")
    return suffix


def write_avatar_bytes(*, data_root: Path, user_id: str, suffix: str, raw: bytes) -> Path:
    if len(raw) > _MAX_AVATAR_BYTES:
        raise ValueError("Avatar exceeds maximum size.")
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
