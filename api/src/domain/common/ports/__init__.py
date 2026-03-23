"""
Canonical re-exports for persistence and retrieval ports (dependency inversion).

Concrete types live in feature packages (``documents``, ``retrieval``, ``evaluation``, ``shared``);
this package provides a single import path for composition roots and use cases.
"""

from domain.projects.documents.asset_repository_port import AssetRepositoryPort
from domain.evaluation.qa_dataset_repository_port import QADatasetRepositoryPort
from domain.common.ports.access_token_issuer_port import AccessTokenIssuerPort
from domain.common.ports.answer_generation_port import AnswerGenerationPort, GenerationPort
from domain.common.ports.authentication_port import AuthenticationPort
from domain.common.ports.benchmark_orchestration_ports import (
    AutoDebugSuggestionsPort,
    BenchmarkFailureAnalysisPort,
    BenchmarkRowProcessingPort,
    BenchmarkSummaryAggregationPort,
    CorrelationComputePort,
    ExplainabilityBuildPort,
)
from domain.common.ports.chat_transcript_port import ChatTranscriptPort
from domain.common.ports.document_ingestion_port import DocumentIngestionPort
from domain.common.ports.gold_qa_benchmark_port import GoldQaBenchmarkPort
from domain.common.ports.manual_evaluation_from_rag_port import ManualEvaluationFromRagPort
from domain.common.ports.project_chain_handle_cache_port import ProjectChainHandleCachePort
from domain.common.ports.project_workspace_port import ProjectWorkspacePort
from domain.common.ports.qa_dataset_entries_port import QADatasetEntriesPort
from domain.common.ports.qa_dataset_generation_port import QaDatasetGenerationPort
from domain.common.ports.query_log_port import QueryLogPort
from domain.common.ports.retrieval_port import RetrievalPort
from domain.common.ports.retrieval_preset_merge_port import RetrievalPresetMergePort
from domain.common.ports.retrieval_settings_resolution_port import RetrievalSettingsResolutionPort
from domain.common.ports.user_repository_port import UserRepositoryPort
from domain.rag.retrieval.vector_store_port import VectorStorePort
from domain.common.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from domain.common.shared.query_log_port import QueryLogPersistencePort

__all__ = [
    "AccessTokenIssuerPort",
    "AuthenticationPort",
    "AnswerGenerationPort",
    "GenerationPort",
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
    "RetrievalPort",
    "ProjectSettingsRepositoryPort",
    "RetrievalPresetMergePort",
    "RetrievalSettingsResolutionPort",
    "UserRepositoryPort",
    "VectorStorePort",
]
