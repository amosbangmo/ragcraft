"""
Canonical re-exports for persistence and retrieval ports (dependency inversion).

Concrete types live in feature packages (``documents``, ``retrieval``, ``evaluation``, ``shared``);
this package provides a single import path for composition roots and use cases.
"""

from src.domain.documents.asset_repository_port import AssetRepositoryPort
from src.domain.evaluation.qa_dataset_repository_port import QADatasetRepositoryPort
from src.domain.ports.answer_generation_port import AnswerGenerationPort
from src.domain.ports.benchmark_orchestration_ports import (
    AutoDebugSuggestionsPort,
    BenchmarkFailureAnalysisPort,
    BenchmarkRowProcessingPort,
    BenchmarkSummaryAggregationPort,
    CorrelationComputePort,
    ExplainabilityBuildPort,
)
from src.domain.ports.chat_transcript_port import ChatTranscriptPort
from src.domain.ports.document_ingestion_port import DocumentIngestionPort
from src.domain.ports.gold_qa_benchmark_port import GoldQaBenchmarkPort
from src.domain.ports.manual_evaluation_from_rag_port import ManualEvaluationFromRagPort
from src.domain.ports.project_chain_handle_cache_port import ProjectChainHandleCachePort
from src.domain.ports.project_workspace_port import ProjectWorkspacePort
from src.domain.ports.qa_dataset_entries_port import QADatasetEntriesPort
from src.domain.ports.qa_dataset_generation_port import QaDatasetGenerationPort
from src.domain.ports.query_log_port import QueryLogPort
from src.domain.ports.retrieval_preset_merge_port import RetrievalPresetMergePort
from src.domain.ports.retrieval_settings_resolution_port import RetrievalSettingsResolutionPort
from src.domain.retrieval.vector_store_port import VectorStorePort
from src.domain.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from src.domain.shared.query_log_port import QueryLogPersistencePort
from src.domain.ports.user_repository_port import UserRepositoryPort

__all__ = [
    "AnswerGenerationPort",
    "ChatTranscriptPort",
    "AssetRepositoryPort",
    "AutoDebugSuggestionsPort",
    "BenchmarkFailureAnalysisPort",
    "BenchmarkRowProcessingPort",
    "BenchmarkSummaryAggregationPort",
    "CorrelationComputePort",
    "DocumentIngestionPort",
    "ExplainabilityBuildPort",
    "GoldQaBenchmarkPort",
    "ManualEvaluationFromRagPort",
    "ProjectChainHandleCachePort",
    "ProjectWorkspacePort",
    "QADatasetEntriesPort",
    "QADatasetGenerationPort",
    "QADatasetRepositoryPort",
    "QueryLogPersistencePort",
    "QueryLogPort",
    "ProjectSettingsRepositoryPort",
    "RetrievalPresetMergePort",
    "RetrievalSettingsResolutionPort",
    "UserRepositoryPort",
    "VectorStorePort",
]
