"""Import path rewrites after physical migration."""
from __future__ import annotations

from pathlib import Path


def apply_text_rewrites(root: Path, api: Path, fe: Path) -> None:
    exts = {".py", ".md", ".toml", ".sh", ".ps1", "Dockerfile"}
    skip_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}

    rules: list[tuple[str, str]] = []

    def add(old: str, new: str) -> None:
        rules.append((old, new))

    add("from apps.api.", "from interfaces.http.")
    add("import apps.api.", "import interfaces.http.")
    add("from src.domain.ports.", "from domain.common.ports.")
    add("from domain.ports import", "from domain.common.ports import")
    add("from src.domain.shared.", "from domain.common.shared.")
    add("from src.domain.documents.", "from domain.projects.documents.")
    add("from src.domain.chat.", "from domain.rag.chat.")
    add("from src.domain.retrieval.", "from domain.rag.retrieval.")

    for m in (
        "benchmark_comparison",
        "benchmark_failure_analysis",
        "benchmark_metric_taxonomy",
        "benchmark_result",
        "llm_judge_constants",
        "llm_judge_result",
        "manual_evaluation_result",
        "multimodal_metrics",
        "qa_dataset_entry",
        "qa_dataset_proposal",
        "evaluation_display_text",
    ):
        add(f"from src.domain.{m} ", f"from domain.evaluation.{m} ")
        add(f"from src.domain.{m}\n", f"from domain.evaluation.{m}\n")
        add(f"from src.domain.{m} import", f"from domain.evaluation.{m} import")

    add("from src.domain.authenticated_principal", "from domain.auth.authenticated_principal")
    add("from src.domain.project ", "from domain.projects.project ")
    add("from src.domain.project\n", "from domain.projects.project\n")
    add("from src.domain.project import", "from domain.projects.project import")
    add("from src.domain.project_settings", "from domain.projects.project_settings")
    add("from src.domain.buffered_document_upload", "from domain.projects.buffered_document_upload")
    add("from src.domain.ingestion_diagnostics", "from domain.common.ingestion_diagnostics")

    for m in (
        "chat_message",
        "rag_response",
        "pipeline_latency",
        "pipeline_payloads",
        "prompt_source",
        "query_intent",
        "query_log_ingress_payload",
        "query_log_timestamp",
        "rag_inspect_answer_run",
        "retrieved_asset",
        "retrieval_filters",
        "retrieval_presets",
        "retrieval_settings",
        "retrieval_settings_override_spec",
        "retrieval_strategy",
        "summary_document_fusion",
        "summary_recall_document",
    ):
        add(f"from src.domain.{m} ", f"from domain.rag.{m} ")
        add(f"from src.domain.{m}\n", f"from domain.rag.{m}\n")
        add(f"from src.domain.{m} import", f"from domain.rag.{m} import")

    add("from src.domain.evaluation.", "from domain.evaluation.")
    add("from src.application.use_cases.chat.orchestration.", "from application.orchestration.rag.")
    add("from src.application.chat.policies.", "from application.policies.")
    add("from src.application.auth.dtos", "from application.dto.auth")
    add("from src.application.projects.dtos", "from application.dto.projects")
    add("from src.application.ingestion.dtos", "from application.dto.ingestion")
    add("from src.application.settings.dtos", "from application.dto.settings")
    add("from src.application.evaluation.dtos", "from application.dto.evaluation")
    add("from src.application.evaluation.benchmark_export_dtos", "from application.dto.benchmark_export")
    add("from src.application.rag.dtos", "from application.dto.rag")
    add("from src.application.http.wire", "from application.http.wire")
    add("from src.application.json_wire", "from application.http.wire.json_wire")
    add("from src.application.frontend_support.", "from application.services.")
    add("from src.application.users.avatar_upload_policy", "from application.policies.avatar_upload_policy")
    add("from src.application.auth.identity_ports", "from application.ports.identity_ports")
    add("from src.application.settings.retrieval_merge_default", "from application.services.retrieval_merge_default")
    add(
        "from src.application.settings.retrieval_preset_merge_port",
        "from application.services.retrieval_preset_merge_port",
    )
    add(
        "from src.application.settings.retrieval_settings_tuner",
        "from application.services.retrieval_settings_tuner",
    )

    for m in (
        "rag_pipeline_orchestration",
        "benchmark_execution",
        "build_benchmark_export_artifacts",
        "gold_qa_benchmark_adapter",
    ):
        add(
            f"from src.application.use_cases.evaluation.{m}",
            f"from application.orchestration.evaluation.{m}",
        )

    add("from src.infrastructure.adapters.rag.", "from infrastructure.rag.")
    add("from src.infrastructure.adapters.evaluation.", "from infrastructure.evaluation.")
    add("from src.infrastructure.adapters.qa_dataset.", "from infrastructure.evaluation.")
    add("from src.infrastructure.adapters.auth.", "from infrastructure.auth.")
    add("from src.infrastructure.adapters.filesystem.", "from infrastructure.storage.")
    add("from src.infrastructure.adapters.query_logging.", "from infrastructure.observability.")
    add("from src.infrastructure.adapters.workspace.", "from infrastructure.persistence.")
    add("from src.infrastructure.adapters.document.", "from infrastructure.rag.")
    add("from src.infrastructure.adapters.sqlite.", "from infrastructure.persistence.sqlite.")
    add(
        "from src.infrastructure.adapters.summary_recall_document_adapter",
        "from infrastructure.rag.summary_recall_document_adapter",
    )
    add("from src.infrastructure.vectorstores.", "from infrastructure.rag.vectorstores.")
    add("from src.infrastructure.llm.", "from infrastructure.rag.llm.")
    add("from src.infrastructure.ingestion.", "from infrastructure.rag.ingestion.")
    add("from src.infrastructure.web.", "from infrastructure.rag.web.")
    add("from src.infrastructure.logging.", "from infrastructure.observability.logging.")
    add("from src.infrastructure.caching.", "from infrastructure.persistence.caching.")
    add("from src.infrastructure.persistence.", "from infrastructure.persistence.")
    add("from src.auth.", "from infrastructure.auth.")
    add("from src.core.", "from infrastructure.config.")
    add("from src.composition.", "from composition.")
    add("from src.application.", "from application.")
    add("from src.domain.", "from domain.")
    add("from src.infrastructure.", "from infrastructure.")
    add("from src.ui.", "from components.shared.")
    add("from src.frontend_gateway.", "from services.")
    add("from src.frontend_gateway ", "from services ")
    add("import src.frontend_gateway", "import services")

    # Patch strings / dynamic imports still using dotted ``src.*`` (tests, docstrings).
    add("src.domain.ports.", "domain.common.ports.")
    add("src.domain.shared.", "domain.common.shared.")
    add("src.domain.documents.", "domain.projects.documents.")
    add("src.domain.chat.", "domain.rag.chat.")
    add("src.domain.retrieval.", "domain.rag.retrieval.")
    add("src.domain.evaluation.", "domain.evaluation.")
    add("src.infrastructure.adapters.rag.", "infrastructure.rag.")
    add("src.infrastructure.adapters.evaluation.", "infrastructure.evaluation.")
    add("src.infrastructure.adapters.qa_dataset.", "infrastructure.evaluation.")
    add("src.infrastructure.adapters.auth.", "infrastructure.auth.")
    add("src.infrastructure.adapters.filesystem.", "infrastructure.storage.")
    add("src.infrastructure.adapters.query_logging.", "infrastructure.observability.")
    add("src.infrastructure.adapters.workspace.", "infrastructure.persistence.")
    add("src.infrastructure.adapters.document.", "infrastructure.rag.")
    add("src.infrastructure.adapters.sqlite.", "infrastructure.persistence.sqlite.")
    add(
        "src.infrastructure.adapters.summary_recall_document_adapter",
        "infrastructure.rag.summary_recall_document_adapter",
    )
    add("src.infrastructure.vectorstores.", "infrastructure.rag.vectorstores.")
    add("src.infrastructure.llm.", "infrastructure.rag.llm.")
    add("src.infrastructure.ingestion.", "infrastructure.rag.ingestion.")
    add("src.infrastructure.web.", "infrastructure.rag.web.")
    add("src.infrastructure.logging.", "infrastructure.observability.logging.")
    add("src.infrastructure.caching.", "infrastructure.persistence.caching.")
    add("src.infrastructure.persistence.", "infrastructure.persistence.")
    add("src.infrastructure.adapters.", "infrastructure.")
    add("src.auth.", "infrastructure.auth.")
    add("src.core.", "infrastructure.config.")
    add("src.composition.", "composition.")
    add("import src.composition", "import composition")
    add("from src.composition import", "from composition import")
    add("src.application.", "application.")
    add("src.domain.", "domain.")
    add("src.infrastructure.", "infrastructure.")

    rules.sort(key=lambda x: len(x[0]), reverse=True)

    def rewrite_file(path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        orig = text
        for old, new in rules:
            text = text.replace(old, new)
        if text != orig:
            path.write_text(text, encoding="utf-8")

    for base in (root, api, fe):
        for p in base.rglob("*"):
            if any(x in p.parts for x in skip_dirs):
                continue
            if p.name in ("run_structure_migration.py", "migrate_phases.py", "migrate_rewrite.py"):
                continue
            if p.is_file() and (p.suffix in exts or p.name == "Dockerfile"):
                rewrite_file(p)
