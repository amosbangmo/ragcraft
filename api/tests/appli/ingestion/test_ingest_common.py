from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from application.dto.ingestion import DocumentReplacementSummary
from application.use_cases.ingestion.ingest_common import (
    default_empty_replacement_info,
    finalize_ingestion_pipeline,
    resolve_project_file_path,
)
from domain.common.ingestion_diagnostics import IngestionDiagnostics
from domain.projects.documents.stored_multimodal_asset import StoredMultimodalAsset
from domain.projects.project import Project


def test_resolve_project_file_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("domain.projects.project.get_data_root", lambda: tmp_path)
    p = Project(user_id="u", project_id="demo")
    assert resolve_project_file_path(p, "a.pdf") == p.path / "a.pdf"


def test_default_empty_replacement_info() -> None:
    s = default_empty_replacement_info()
    assert s.deleted_vectors == 0


def test_finalize_raises_without_raw_assets() -> None:
    project = MagicMock()
    with pytest.raises(ValueError, match="No raw assets"):
        finalize_ingestion_pipeline(
            project=project,
            user_id="u",
            project_id="p",
            source_file="f.txt",
            summary_documents=[],
            raw_assets=[],
            diagnostics=IngestionDiagnostics(),
            replacement_info=DocumentReplacementSummary([], 0, 0),
            asset_repository=MagicMock(),
            vector_index=MagicMock(),
            invalidate_project_chain=MagicMock(),
        )


def test_finalize_stored_asset_and_indexing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("domain.projects.project.get_data_root", lambda: tmp_path)
    project = Project(user_id="u", project_id="p")
    inv = MagicMock()
    asset_repo = MagicMock()
    vec = MagicMock()
    vec.index_documents.return_value = (None, 12.5)

    raw = {
        "doc_id": "d1",
        "user_id": "u",
        "project_id": "p",
        "source_file": "f.txt",
        "content_type": "text",
        "raw_content": "x",
        "summary": "s",
        "metadata": {},
        "created_at": None,
    }
    doc = MagicMock()
    doc.page_content = "pc"
    doc.metadata = {"k": "v"}

    rep = DocumentReplacementSummary([], 0, 0)
    diag = IngestionDiagnostics(extraction_ms=1.0, summarization_ms=2.0)
    out = finalize_ingestion_pipeline(
        project=project,
        user_id="u",
        project_id="p",
        source_file="f.txt",
        summary_documents=[doc],
        raw_assets=[raw],
        diagnostics=diag,
        replacement_info=rep,
        asset_repository=asset_repo,
        vector_index=vec,
        invalidate_project_chain=inv,
    )
    assert len(out.raw_assets) == 1
    assert isinstance(out.raw_assets[0], StoredMultimodalAsset)
    asset_repo.upsert_asset.assert_called_once()
    inv.assert_called_once_with("u", "p")
    assert out.diagnostics.indexing_ms == 12.5


def test_finalize_accepts_stored_multimodal_instances(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("domain.projects.project.get_data_root", lambda: tmp_path)
    project = Project(user_id="u", project_id="p")
    sa = StoredMultimodalAsset(
        doc_id="d",
        user_id="u",
        project_id="p",
        source_file="f.txt",
        content_type="text",
        raw_content="r",
        summary="s",
        metadata={},
        created_at=None,
    )
    vec = MagicMock()
    vec.index_documents.return_value = (None, 0.0)
    finalize_ingestion_pipeline(
        project=project,
        user_id="u",
        project_id="p",
        source_file="f.txt",
        summary_documents=[],
        raw_assets=[sa],
        diagnostics=IngestionDiagnostics(),
        replacement_info=DocumentReplacementSummary([], 0, 0),
        asset_repository=MagicMock(),
        vector_index=vec,
        invalidate_project_chain=MagicMock(),
    )
