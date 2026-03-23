"""
Gold QA evaluation, manual evaluation, QA dataset management, retrieval logs, and benchmark exports.

**Layout**
- ``application.dto`` / ``application.use_cases.evaluation`` — commands and orchestration entrypoints.
- Metric helpers and judges live in :mod:`infrastructure.evaluation` (wired via composition).
- :mod:`application.evaluation.benchmark_report_formatter` — portable report artifacts.

**Composition** — :class:`~composition.application_container.BackendApplicationContainer` exposes
``evaluation_*`` use-case factories; FastAPI resolves them via ``interfaces.http.dependencies``.
"""

from __future__ import annotations

__all__: list[str] = []
