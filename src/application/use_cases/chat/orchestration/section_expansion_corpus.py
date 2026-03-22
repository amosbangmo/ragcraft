"""Build the expanded asset corpus for section-aware retrieval (application-owned policy)."""

from __future__ import annotations

from src.application.use_cases.chat.orchestration.ports import DocstoreRecallReadPort
from src.domain.project import Project


def build_section_expansion_corpus(
    *,
    project: Project,
    recalled_raw_assets: list[dict],
    docstore: DocstoreRecallReadPort,
) -> list[dict]:
    seen_files: set[str] = set()
    source_files: list[str] = []
    for asset in recalled_raw_assets:
        sf = asset.get("source_file")
        if not sf:
            continue
        s = str(sf).strip()
        if not s or s in seen_files:
            continue
        seen_files.add(s)
        source_files.append(s)

    if not source_files:
        return docstore.list_assets_for_project(
            user_id=project.user_id,
            project_id=project.project_id,
        )

    by_doc: dict[str, dict] = {}
    for s in source_files:
        for row in docstore.list_assets_for_source_file(
            user_id=project.user_id,
            project_id=project.project_id,
            source_file=s,
        ):
            did = row.get("doc_id")
            if did:
                by_doc[str(did)] = row
    return list(by_doc.values())
