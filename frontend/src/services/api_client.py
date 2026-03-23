"""
Canonical frontend ↔ backend integration surface.

Streamlit code should import from here (or :mod:`services.streamlit_api_client` / :mod:`services.protocol`)
rather than reaching into :mod:`services.http_client` or backend packages.

**HTTP contract** parsing and request bodies live in:

- :mod:`services.http_payloads` — JSON → wire dataclasses
- :mod:`services.api_contract_models` — projects, chat, retrieval settings, ingestion, QA rows
- :mod:`services.evaluation_wire_models` / :mod:`services.evaluation_wire_parse` — evaluation payloads

The typed HTTP implementation is :class:`~services.http_client.HttpBackendClient`.
"""

from __future__ import annotations

from services.api_contract_models import (  # noqa: F401
    DeleteDocumentPayload,
    EffectiveRetrievalSettingsPayload,
    IngestDocumentPayload,
    ProjectSettingsPayload,
    QADatasetEntryPayload,
    RAGAnswer,
    RetrievalFilters,
    UpdateProjectRetrievalSettingsCommand,
    WorkspaceProject,
)
from services.evaluation_wire_models import BenchmarkResult, ManualEvaluationResult  # noqa: F401
from services.http_client import HttpBackendClient  # noqa: F401
from services.http_transport import HttpTransport  # noqa: F401
from services.streamlit_api_client import (  # noqa: F401
    get_backend_client,
    get_frontend_backend_settings,
    is_http_backend_mode,
)

__all__ = [
    "BenchmarkResult",
    "DeleteDocumentPayload",
    "EffectiveRetrievalSettingsPayload",
    "HttpBackendClient",
    "HttpTransport",
    "IngestDocumentPayload",
    "ManualEvaluationResult",
    "ProjectSettingsPayload",
    "QADatasetEntryPayload",
    "RAGAnswer",
    "RetrievalFilters",
    "UpdateProjectRetrievalSettingsCommand",
    "WorkspaceProject",
    "get_backend_client",
    "get_frontend_backend_settings",
    "is_http_backend_mode",
]
