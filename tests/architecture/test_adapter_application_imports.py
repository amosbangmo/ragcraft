"""
Infrastructure adapters must not import ``src.application``.

Composition (:mod:`src.composition`) and tests may import application use cases to wire the graph.
Domain policies live in ``src.domain``; application orchestration is not a dependency of adapters.
"""

from __future__ import annotations

from pathlib import Path

from tests.architecture.import_scanner import imported_top_level_modules, iter_python_files

REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_ROOT = REPO_ROOT / "src" / "infrastructure" / "adapters"


def _relative_adapter_path(path: Path) -> str:
    return path.relative_to(ADAPTER_ROOT).as_posix()


def test_adapters_do_not_import_application() -> None:
    violations: list[str] = []
    for path in iter_python_files(ADAPTER_ROOT):
        for mod in imported_top_level_modules(path):
            if mod != "src.application" and not mod.startswith("src.application."):
                continue
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
    assert not violations, (
        "Adapter modules under src/infrastructure/adapters must not depend on src.application "
        "(move shared DTOs to domain, wire use cases in composition).\n" + "\n".join(violations)
    )
