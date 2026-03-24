"""
Canonical frontend ↔ backend integration surface.

Streamlit **pages** and **components** import backend types and helpers **only** from this
module — not from transport/protocol subpackages or application/composition packages.

**HTTP contract** parsing and low-level helpers live under:

- :mod:`services.backend.http_payloads` — JSON → wire dataclasses
- :mod:`services.contract.api_contract_models` — projects, chat, retrieval settings, ingestion, QA rows
- :mod:`services.contract.evaluation_wire_models` / :mod:`services.contract.evaluation_wire_parse` — evaluation payloads
"""

from __future__ import annotations

from services.backend.backend_client_protocol import BackendClient  # noqa: F401
from services.backend.backend_session import (  # noqa: F401
    get_backend_client,
    get_frontend_backend_settings,
)
from services.backend.http_backend_client import HttpBackendClient  # noqa: F401
from services.backend.http_transport import HttpTransport  # noqa: F401
from services.contract.api_contract_models import (  # noqa: F401
    DeleteDocumentPayload,
    EffectiveRetrievalSettingsPayload,
    IngestDocumentPayload,
    ProjectSettingsPayload,
    QADatasetEntryPayload,
    RAGAnswer,
    RetrievalFilters,
    RetrievalSettingsPayload,
    SummaryRecallDocumentView,
    SummaryRecallPreviewPayload,
    UpdateProjectRetrievalSettingsCommand,
    WorkspaceProject,
)
from services.contract.evaluation_wire_models import (  # noqa: F401
    JUDGE_FAILURE_REASON,
    BenchmarkResult,
    ManualEvaluationResult,
)
from services.contract.evaluation_wire_parse import (  # noqa: F401
    coerce_benchmark_result,
    is_manual_evaluation_result_like,
)
from services.evaluation.benchmark_compare_ui import (  # noqa: F401
    LOWER_IS_BETTER_METRICS,
    compare_benchmark_failure_counts,
    compare_benchmark_summaries,
)
from services.evaluation.evaluation_display_ui import format_bool_toggle_on_off  # noqa: F401
from services.evaluation.failure_analysis_ui import FailureAnalysisService  # noqa: F401
from services.evaluation.query_log_ui import parse_query_log_timestamp  # noqa: F401
from services.retrieval.retrieval_preset_merge_service import (  # noqa: F401
    RetrievalPresetMergePort,
    default_retrieval_preset_merge_port,
)
from services.retrieval.retrieval_preset_ui import (  # noqa: F401
    PRESET_DESCRIPTIONS,
    PRESET_SELECT_ORDER,
    PRESET_UI_LABELS,
    RetrievalPreset,
    parse_retrieval_preset,
)

# Alias for gold-QA rows (wire-only).
QADatasetEntry = QADatasetEntryPayload

__all__ = [
    "BackendClient",
    "BenchmarkResult",
    "DeleteDocumentPayload",
    "EffectiveRetrievalSettingsPayload",
    "FailureAnalysisService",
    "HttpBackendClient",
    "HttpTransport",
    "IngestDocumentPayload",
    "JUDGE_FAILURE_REASON",
    "LOWER_IS_BETTER_METRICS",
    "ManualEvaluationResult",
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
    "RetrievalSettingsPayload",
    "SummaryRecallDocumentView",
    "SummaryRecallPreviewPayload",
    "UpdateProjectRetrievalSettingsCommand",
    "WorkspaceProject",
    "compare_benchmark_failure_counts",
    "compare_benchmark_summaries",
    "coerce_benchmark_result",
    "default_retrieval_preset_merge_port",
    "format_bool_toggle_on_off",
    "get_backend_client",
    "get_frontend_backend_settings",
    "is_manual_evaluation_result_like",
    "parse_query_log_timestamp",
    "parse_retrieval_preset",
]
