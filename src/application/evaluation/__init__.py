"""
Gold QA evaluation, manual evaluation, QA dataset management, retrieval logs, and benchmark exports.

**Layout**
- ``dtos`` — commands and queries for use-case entrypoints (plus ``GenerateQaDatasetCommand``).
- ``src.application.use_cases.evaluation`` — orchestration; metric helpers and judges are implemented in
  :mod:`src.infrastructure.adapters.evaluation` (wired via composition), e.g. :class:`~src.infrastructure.adapters.evaluation.evaluation_service.EvaluationService`.
- ``benchmark_export_dtos`` / ``benchmark_report_formatter`` — portable report artifacts.

**Composition** — :class:`~src.composition.application_container.BackendApplicationContainer` exposes
``evaluation_*`` use-case factories; FastAPI resolves them via ``apps.api.dependencies``.
"""

from __future__ import annotations

from . import dtos

__all__ = ["dtos"]
