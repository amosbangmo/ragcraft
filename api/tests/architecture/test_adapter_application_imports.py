"""
Modules under ``api/src/infrastructure`` must not import ``application``.

Composition and tests may import application use cases to wire the graph.
Domain policies live under ``domain``; application orchestration is not a dependency of infrastructure.
"""

from __future__ import annotations

from pathlib import Path

from architecture.import_scanner import imported_top_level_modules, iter_python_files

REPO_ROOT = Path(__file__).resolve().parents[3]
INFRA_ROOT = REPO_ROOT / "api" / "src" / "infrastructure"


def _relative_adapter_path(path: Path) -> str:
    return path.relative_to(INFRA_ROOT).as_posix()


def test_adapters_do_not_import_application() -> None:
    violations: list[str] = []
    for path in iter_python_files(INFRA_ROOT):
        rel = path.relative_to(INFRA_ROOT)
        if rel.parts[:1] == ("auth",) and rel.name == "auth_credentials.py":
            # FastAPI OAuth2 form wiring imports login/register use cases (transport-adjacent).
            continue
        for mod in imported_top_level_modules(path):
            if mod != "application" and not mod.startswith("application."):
                continue
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
    assert not violations, (
        "Infrastructure modules under api/src/infrastructure must not depend on application.* "
        "(move shared DTOs to domain, wire use cases in composition).\n" + "\n".join(violations)
    )
