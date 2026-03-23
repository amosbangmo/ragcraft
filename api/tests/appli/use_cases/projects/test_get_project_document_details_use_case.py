from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from application.dto.projects import ProjectDocumentDetailRow
from application.use_cases.projects.get_project_document_details import GetProjectDocumentDetailsUseCase


def test_document_details_returns_typed_rows(tmp_path: Path) -> None:
    (tmp_path / "a.pdf").write_bytes(b"x")

    resolve = MagicMock()
    proj = MagicMock()
    proj.path = tmp_path
    resolve.execute.return_value = proj
    assets = MagicMock()
    assets.count_assets_for_source_file.return_value = 2
    assets.get_asset_stats_for_source_file.return_value = {
        "text_count": 1,
        "table_count": 0,
        "image_count": 1,
        "latest_ingested_at": "2024-01-01T00:00:00",
    }

    uc = GetProjectDocumentDetailsUseCase(resolve_project=resolve, asset_repository=assets)
    rows = uc.execute(user_id="u", project_id="p", document_names=["a.pdf"])

    assert len(rows) == 1
    r = rows[0]
    assert isinstance(r, ProjectDocumentDetailRow)
    assert r.name == "a.pdf"
    assert r.project_id == "p"
    assert r.size_bytes == 1
    assert r.asset_count == 2
    assert r.latest_ingested_at == "2024-01-01T00:00:00"
