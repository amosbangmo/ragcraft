import os
from pathlib import Path


DEFAULT_DATA_ROOT = "data"
DEFAULT_DB_FILENAME = "ragcraft.db"


def get_data_root() -> Path:
    """
    Return the root directory used for all persisted application data.

    This becomes the single source of truth for:
    - user folders
    - project folders
    - avatar storage
    - the default SQLite location
    """
    return Path(os.getenv("RAGCRAFT_DATA_PATH", DEFAULT_DATA_ROOT))


def get_sqlite_db_path() -> Path:
    """
    Return the SQLite database path.

    Priority:
    1. SQLITE_DB_PATH if explicitly provided
    2. <data_root>/ragcraft.db otherwise
    """
    configured_path = os.getenv("SQLITE_DB_PATH")
    if configured_path and configured_path.strip():
        return Path(configured_path.strip())

    return get_data_root() / DEFAULT_DB_FILENAME
