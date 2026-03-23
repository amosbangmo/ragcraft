"""
Application layer must stay free of delivery frameworks, storage drivers, and vector-store libs.

Complements :mod:`tests.architecture.test_layer_boundaries` with explicit forbidden technology imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture.import_scanner import any_module_matches, imported_top_level_modules, iter_python_files

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def application_files() -> list[Path]:
    return iter_python_files(REPO_ROOT / "src" / "application")


@pytest.fixture(scope="module")
def use_case_files() -> list[Path]:
    root = REPO_ROOT / "src" / "application" / "use_cases"
    return iter_python_files(root) if root.is_dir() else []


def test_application_avoids_delivery_and_storage_tech_imports(application_files: list[Path]) -> None:
    forbidden = (
        "fastapi",
        "starlette",
        "uvicorn",
        "streamlit",
        "sqlite3",
        "faiss",
        "langchain",
        "langgraph",
    )
    violations: list[str] = []
    for path in application_files:
        mods = imported_top_level_modules(path)
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    msg = (
        "Application code must not import HTTP servers, Streamlit, sqlite3, FAISS, or LangChain packages. "
        "Keep those in infrastructure adapters or delivery layers.\n"
    )
    assert not violations, msg + "\n".join(violations)


def test_use_cases_do_not_import_frontend_gateway(use_case_files: list[Path]) -> None:
    """Orchestration lives in application; UI gateway is a delivery concern."""
    if not use_case_files:
        pytest.skip("no use_cases package")
    violations: list[str] = []
    for path in use_case_files:
        for mod in imported_top_level_modules(path):
            if mod == "src.frontend_gateway" or mod.startswith("src.frontend_gateway."):
                violations.append(f"{path.relative_to(REPO_ROOT)}: imports {mod}")
    assert not violations, (
        "Use case modules must not import ``src.frontend_gateway``; depend on ports and DTOs only.\n"
        + "\n".join(violations)
    )


@pytest.fixture(scope="module")
def router_files() -> list[Path]:
    return iter_python_files(REPO_ROOT / "apps" / "api" / "routers")


def test_application_layer_imports_no_jwt_libraries(application_files: list[Path]) -> None:
    violations: list[str] = []
    for path in application_files:
        text = path.read_text(encoding="utf-8")
        for token in ("import jwt", "from jwt", "PyJWT"):
            if token in text:
                violations.append(f"{path.relative_to(REPO_ROOT)}: contains {token!r}")
    assert not violations, (
        "Application layer must not import JWT libraries; keep token crypto in infrastructure adapters.\n"
        + "\n".join(violations)
    )


def test_api_routers_avoid_persistence_and_vector_internals(router_files: list[Path]) -> None:
    forbidden = (
        "src.infrastructure.persistence",
        "src.infrastructure.vectorstores",
        "src.infrastructure.llm",
        "sqlite3",
        "faiss",
    )
    violations: list[str] = []
    for path in router_files:
        mods = imported_top_level_modules(path)
        bad = any_module_matches(mods, prefixes=forbidden)
        for m in bad:
            violations.append(f"{path.relative_to(REPO_ROOT)}: imports {m}")
    msg = (
        "API routers must not import persistence, vector stores, LLM internals, sqlite3, or faiss; "
        "use FastAPI dependencies and use cases.\n"
    )
    assert not violations, msg + "\n".join(violations)
