"""
Gold QA evaluation, manual evaluation, QA dataset management, retrieval logs, and benchmark exports.

**Layout**
- ``dtos`` — commands and queries for use-case entrypoints (plus ``GenerateQaDatasetCommand``).
- ``use_cases/`` — orchestration; benchmark row math stays in ``src/services/*`` behind
  :class:`~src.infrastructure.services.evaluation_service.EvaluationService`.
- ``benchmark_export_dtos`` / ``benchmark_report_formatter`` — portable report artifacts.

**Composition** — :class:`~src.composition.application_container.BackendApplicationContainer` exposes
``evaluation_*`` use-case factories; FastAPI resolves them via ``apps.api.dependencies``.
"""

from __future__ import annotations

from . import dtos

__all__ = ["dtos"]
