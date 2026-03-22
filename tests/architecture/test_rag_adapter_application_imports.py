"""
RAG infrastructure adapters must not pull in ``src.application`` (except documented allowlist).

Domain policies belong in ``src.domain``; application orchestration stays above adapters.
``retrieval_settings_service.py`` intentionally subclasses application :class:`RetrievalSettingsTuner`.
"""

from __future__ import annotations

from pathlib import Path

from tests.architecture.import_scanner import imported_top_level_modules, iter_python_files

REPO_ROOT = Path(__file__).resolve().parents[2]
RAG_ADAPTER_DIR = REPO_ROOT / "src" / "infrastructure" / "adapters" / "rag"

_ALLOW_APPLICATION_IMPORTS = frozenset(
    {
        "retrieval_settings_service.py",
    }
)


def test_rag_adapters_do_not_import_application_except_allowlist() -> None:
    violations: list[str] = []
    for path in iter_python_files(RAG_ADAPTER_DIR):
        if path.name in _ALLOW_APPLICATION_IMPORTS:
            continue
        for mod in imported_top_level_modules(path):
            if mod == "src.application" or mod.startswith("src.application."):
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
    assert not violations, (
        "RAG adapter modules must not depend on src.application "
        "(move shared logic to domain or wire via composition). Exceptions: "
        + ", ".join(sorted(_ALLOW_APPLICATION_IMPORTS))
        + ".\n"
        + "\n".join(violations)
    )
