from __future__ import annotations

import json
import logging

from domain.common.ingestion_diagnostics import IngestionDiagnostics


def log_ingestion_diagnostics(
    *,
    user_id: str,
    project_id: str,
    source_file: str,
    diagnostics: IngestionDiagnostics,
) -> None:
    log = logging.getLogger("ragcraft.ingestion")
    try:
        log.info(
            json.dumps(
                {
                    "event": "ingestion_diagnostics",
                    "user_id": user_id,
                    "project_id": project_id,
                    "source_file": source_file,
                    **diagnostics.to_dict(),
                },
                ensure_ascii=False,
            )
        )
    except Exception:
        return
