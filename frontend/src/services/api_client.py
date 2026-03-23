"""
Canonical frontend ↔ backend integration surface.

Streamlit **pages** and **components** should import backend types and helpers **only** from this
module — not from :mod:`services.http_client`, legacy protocol modules, or application/composition
packages directly.

**HTTP contract** parsing and low-level helpers remain in:

- :mod:`services.http_payloads` — JSON → wire dataclasses
- :mod:`services.api_contract_models` — projects, chat, retrieval settings, ingestion, QA rows
- :mod:`services.evaluation_wire_models` / :mod:`services.evaluation_wire_parse` — evaluation payloads
"""

from __future__ import annotations

from application.frontend_support.backend_client_protocol import BackendClient  # noqa: F401
from application.frontend_support.http_backend_client import HttpBackendClient  # noqa: F401
from application.frontend_support.streamlit_backend_access import (  # noqa: F401
    get_backend_client,
    get_frontend_backend_settings,
    is_http_backend_mode,
)
from application.frontend_support.view_models import (  # noqa: F401
    LOWER_IS_BETTER_METRICS,
    BenchmarkResult,
    FailureAnalysisService,
    JUDGE_FAILURE_REASON,
    ManualEvaluationResult,
    PipelineBuildResult,
    PRESET_DESCRIPTIONS,
    PRESET_SELECT_ORDER,
    PRESET_UI_LABELS,
    QADatasetEntry,
    RetrievalFilters,
    RetrievalPreset,
    RetrievalSettings,
    compare_benchmark_failure_counts,
    compare_benchmark_summaries,
    coerce_benchmark_result,
    format_bool_toggle_on_off,
    is_manual_evaluation_result_like,
    parse_query_log_timestamp,
    parse_retrieval_preset,
)
from application.services.retrieval_preset_merge_port import (  # noqa: F401
    RetrievalPresetMergePort,
    default_retrieval_preset_merge_port,
)
from services.api_contract_models import (  # noqa: F401
    DeleteDocumentPayload,
    EffectiveRetrievalSettingsPayload,
    IngestDocumentPayload,
    ProjectSettingsPayload,
    QADatasetEntryPayload,
    RAGAnswer,
    UpdateProjectRetrievalSettingsCommand,
    WorkspaceProject,
)
from services.http_transport import HttpTransport  # noqa: F401

__all__ = [
    "BackendClient",
    "BenchmarkResult",
    "DeleteDocumentPayload",
    "EffectiveRetrievalSettingsPayload",
    "FailureAnalysisService",
    "HttpBackendClient",
    "HttpTransport",
    "InProcessBackendClient",
    "IngestDocumentPayload",
    "JUDGE_FAILURE_REASON",
    "LOWER_IS_BETTER_METRICS",
    "ManualEvaluationResult",
    "PipelineBuildResult",
    "PRESET_DESCRIPTIONS",
    "PRESET_SELECT_ORDER",
    "PRESET_UI_LABELS",
    "ProjectSettingsPayload",
    "QADatasetEntry",
    "QADatasetEntryPayload",
    "RAGAnswer",
    "RetrievalFilters",
    "RetrievalPreset",
    "RetrievalPresetMergePort",
    "RetrievalSettings",
    "UpdateProjectRetrievalSettingsCommand",
    "WorkspaceProject",
    "compare_benchmark_failure_counts",
    "compare_benchmark_summaries",
    "coerce_benchmark_result",
    "default_retrieval_preset_merge_port",
    "format_bool_toggle_on_off",
    "get_backend_client",
    "get_frontend_backend_settings",
    "is_http_backend_mode",
    "is_manual_evaluation_result_like",
    "parse_query_log_timestamp",
    "parse_retrieval_preset",
]


def __getattr__(name: str):
    if name == "InProcessBackendClient":
        from application.frontend_support.in_process_backend_client import InProcessBackendClient

        return InProcessBackendClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
