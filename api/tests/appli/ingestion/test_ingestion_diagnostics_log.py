from __future__ import annotations

from unittest.mock import patch

from application.ingestion.ingestion_diagnostics_log import log_ingestion_diagnostics
from domain.common.ingestion_diagnostics import IngestionDiagnostics


def test_log_ingestion_diagnostics_swallows_json_errors() -> None:
    with patch("application.ingestion.ingestion_diagnostics_log.json.dumps", side_effect=TypeError("x")):
        log_ingestion_diagnostics(
            user_id="u",
            project_id="p",
            source_file="f.txt",
            diagnostics=IngestionDiagnostics(),
        )


def test_log_ingestion_diagnostics_happy_path() -> None:
    log_ingestion_diagnostics(
        user_id="u",
        project_id="p",
        source_file="f.txt",
        diagnostics=IngestionDiagnostics(extraction_ms=1.0),
    )
