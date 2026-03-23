import sqlite3
from pathlib import Path

from infrastructure.config.paths import get_sqlite_db_path


def get_db_path() -> Path:
    db_path = get_sqlite_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_app_db():
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            avatar_path TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            source_file TEXT NOT NULL,
            content_type TEXT NOT NULL,
            raw_content TEXT NOT NULL,
            summary TEXT NOT NULL,
            metadata_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS qa_dataset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            question TEXT NOT NULL,
            expected_answer TEXT,
            expected_doc_ids_json TEXT,
            expected_sources_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rag_assets_project
        ON rag_assets(user_id, project_id)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rag_assets_doc_id
        ON rag_assets(doc_id)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_qa_dataset_project
        ON qa_dataset(user_id, project_id)
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            project_id TEXT,
            question TEXT NOT NULL,
            rewritten_query TEXT,
            retrieval_mode TEXT,
            hybrid_retrieval_enabled INTEGER,
            selected_doc_ids_json TEXT,
            recalled_doc_ids_json TEXT,
            confidence REAL,
            answer_preview TEXT,
            latency_ms REAL,
            query_rewrite_ms REAL,
            retrieval_ms REAL,
            reranking_ms REAL,
            prompt_build_ms REAL,
            answer_generation_ms REAL,
            total_latency_ms REAL,
            query_intent TEXT,
            retrieval_strategy_k INTEGER,
            retrieval_strategy_use_hybrid INTEGER,
            retrieval_strategy_apply_filters INTEGER,
            context_compression_chars_before INTEGER,
            context_compression_chars_after INTEGER,
            context_compression_ratio REAL,
            section_expansion_count INTEGER,
            expanded_assets_count INTEGER,
            table_aware_qa_enabled INTEGER,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_query_logs_project_created
        ON query_logs(project_id, created_at)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_query_logs_user_project
        ON query_logs(user_id, project_id)
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_retrieval_settings (
            user_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            retrieval_preset TEXT NOT NULL DEFAULT 'balanced',
            retrieval_advanced INTEGER NOT NULL DEFAULT 0,
            enable_query_rewrite INTEGER NOT NULL DEFAULT 1,
            enable_hybrid_retrieval INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, project_id)
        )
        """
    )

    for ddl in (
        "ALTER TABLE query_logs ADD COLUMN query_intent TEXT",
        "ALTER TABLE query_logs ADD COLUMN retrieval_strategy_k INTEGER",
        "ALTER TABLE query_logs ADD COLUMN retrieval_strategy_use_hybrid INTEGER",
        "ALTER TABLE query_logs ADD COLUMN retrieval_strategy_apply_filters INTEGER",
        "ALTER TABLE query_logs ADD COLUMN context_compression_chars_before INTEGER",
        "ALTER TABLE query_logs ADD COLUMN context_compression_chars_after INTEGER",
        "ALTER TABLE query_logs ADD COLUMN context_compression_ratio REAL",
        "ALTER TABLE query_logs ADD COLUMN section_expansion_count INTEGER",
        "ALTER TABLE query_logs ADD COLUMN expanded_assets_count INTEGER",
        "ALTER TABLE query_logs ADD COLUMN table_aware_qa_enabled INTEGER",
    ):
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                raise

    conn.commit()
    conn.close()
