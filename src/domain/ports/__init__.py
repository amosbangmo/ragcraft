"""
Canonical re-exports for persistence and retrieval ports (dependency inversion).

Concrete types live in feature packages (``documents``, ``retrieval``, ``evaluation``, ``shared``);
this package provides a single import path for composition roots and use cases.
"""

from src.domain.documents.asset_repository_port import AssetRepositoryPort
from src.domain.evaluation.qa_dataset_repository_port import QADatasetRepositoryPort
from src.domain.ports.qa_dataset_entries_port import QADatasetEntriesPort
from src.domain.ports.query_log_port import QueryLogPort
from src.domain.retrieval.vector_store_port import VectorStorePort
from src.domain.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from src.domain.shared.query_log_port import QueryLogPersistencePort

__all__ = [
    "AssetRepositoryPort",
    "QADatasetEntriesPort",
    "QADatasetRepositoryPort",
    "QueryLogPersistencePort",
    "QueryLogPort",
    "ProjectSettingsRepositoryPort",
    "VectorStorePort",
]
