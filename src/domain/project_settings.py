from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectSettings:
    """Persisted retrieval preferences for a single user project workspace."""

    user_id: str
    project_id: str
    retrieval_preset: str
    retrieval_advanced: bool = False
    enable_query_rewrite: bool = True
    enable_hybrid_retrieval: bool = True
