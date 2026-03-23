"""Filesystem phases for run_structure_migration."""
from __future__ import annotations

import shutil
from pathlib import Path


def _move(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise FileExistsError(f"Refusing to overwrite existing {dst}")
    shutil.move(str(src), str(dst))


def _merge_dir(src: Path, dst: Path) -> None:
    if not src.is_dir():
        raise NotADirectoryError(src)
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.iterdir():
        target = dst / p.name
        if p.is_dir():
            _merge_dir(p, target)
        else:
            if target.exists():
                raise FileExistsError(target)
            shutil.move(str(p), str(target))
    src.rmdir()


def _rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _touch_init(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    init = d / "__init__.py"
    if not init.exists():
        init.write_text("", encoding="utf-8")


def phase_clear_partial(api: Path, fe: Path) -> None:
    _rmtree(api)
    _rmtree(fe)


def phase_move_core_to_api(root: Path, api_src: Path) -> None:
    _touch_init(api_src)
    _touch_init(api_src / "interfaces")
    _move(root / "src" / "domain", api_src / "domain")
    _move(root / "src" / "application", api_src / "application")
    _move(root / "src" / "infrastructure", api_src / "infrastructure")
    _move(root / "src" / "composition", api_src / "composition")

    http = api_src / "interfaces" / "http"
    http.mkdir(parents=True, exist_ok=True)
    for name in [
        "__init__.py",
        "config.py",
        "dependencies.py",
        "error_handlers.py",
        "error_payload.py",
        "main.py",
        "openapi_common.py",
        "upload_adapter.py",
    ]:
        p = root / "apps" / "api" / name
        if p.exists():
            _move(p, http / name)
    for sub in ["routers", "schemas"]:
        _move(root / "apps" / "api" / sub, http / sub)

    cfg = api_src / "infrastructure" / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    for p in (root / "src" / "core").iterdir():
        _move(p, cfg / p.name)

    auth_infra = api_src / "infrastructure" / "auth"
    auth_infra.mkdir(parents=True, exist_ok=True)
    for p in (root / "src" / "auth").iterdir():
        _move(p, auth_infra / p.name)


def phase_split_domain(api_src: Path) -> None:
    dom = api_src / "domain"
    staging = dom / "__split_staging"
    _rmtree(staging)
    for name in ("auth", "users", "projects", "rag", "evaluation", "common"):
        (staging / name).mkdir(parents=True)

    def to_staging(bucket: str, src: Path) -> None:
        dst = staging / bucket / src.name
        if dst.exists():
            raise FileExistsError(dst)
        shutil.move(str(src), str(dst))

    _merge_dir(dom / "ports", staging / "common" / "ports")
    _merge_dir(dom / "shared", staging / "common" / "shared")
    to_staging("common", dom / "ingestion_diagnostics.py")
    to_staging("auth", dom / "authenticated_principal.py")
    for name in ("project.py", "project_settings.py", "buffered_document_upload.py"):
        to_staging("projects", dom / name)
    _merge_dir(dom / "documents", staging / "projects" / "documents")
    rag_files = [
        "chat_message.py",
        "rag_response.py",
        "pipeline_latency.py",
        "pipeline_payloads.py",
        "prompt_source.py",
        "query_intent.py",
        "query_log_ingress_payload.py",
        "query_log_timestamp.py",
        "rag_inspect_answer_run.py",
        "retrieved_asset.py",
        "retrieval_filters.py",
        "retrieval_presets.py",
        "retrieval_settings.py",
        "retrieval_settings_override_spec.py",
        "retrieval_strategy.py",
        "summary_document_fusion.py",
        "summary_recall_document.py",
    ]
    for name in rag_files:
        to_staging("rag", dom / name)
    _merge_dir(dom / "chat", staging / "rag" / "chat")
    _merge_dir(dom / "retrieval", staging / "rag" / "retrieval")
    eval_root = [
        "benchmark_comparison.py",
        "benchmark_failure_analysis.py",
        "benchmark_metric_taxonomy.py",
        "benchmark_result.py",
        "llm_judge_constants.py",
        "llm_judge_result.py",
        "manual_evaluation_result.py",
        "multimodal_metrics.py",
        "qa_dataset_entry.py",
        "qa_dataset_proposal.py",
        "evaluation_display_text.py",
    ]
    for name in eval_root:
        to_staging("evaluation", dom / name)
    _merge_dir(dom / "evaluation", staging / "evaluation")
    _touch_init(staging / "users")

    for child in list(dom.iterdir()):
        if child.name == "__split_staging":
            continue
        if child.is_dir():
            _rmtree(child)
        else:
            child.unlink()

    for bucket in ("auth", "users", "projects", "rag", "evaluation", "common"):
        src_b = staging / bucket
        dst_b = dom / bucket
        if dst_b.exists():
            _rmtree(dst_b)
        shutil.move(str(src_b), str(dst_b))

    dom.joinpath("__split_staging").rmdir()
    for sub in ("auth", "users", "projects", "rag", "evaluation", "common"):
        _touch_init(dom / sub)


def phase_application_reshape(api_src: Path) -> None:
    app = api_src / "application"
    orch = app / "orchestration"
    (orch / "rag").mkdir(parents=True, exist_ok=True)
    (orch / "evaluation").mkdir(parents=True, exist_ok=True)
    pol = app / "policies"
    pol.mkdir(parents=True, exist_ok=True)
    dto = app / "dto"
    dto.mkdir(parents=True, exist_ok=True)
    services = app / "services"
    services.mkdir(parents=True, exist_ok=True)
    wire_pkg = app / "http" / "wire"
    wire_pkg.mkdir(parents=True, exist_ok=True)

    orch_src = app / "use_cases" / "chat" / "orchestration"
    for p in orch_src.iterdir():
        if p.name == "__init__.py":
            continue
        _move(p, orch / "rag" / p.name)
    orch_src.joinpath("__init__.py").unlink(missing_ok=True)
    try:
        orch_src.rmdir()
    except OSError:
        pass

    for p in (app / "chat" / "policies").iterdir():
        _move(p, pol / p.name)
    try:
        (app / "chat" / "policies").rmdir()
    except OSError:
        pass

    for name in (
        "rag_pipeline_orchestration.py",
        "benchmark_execution.py",
        "build_benchmark_export_artifacts.py",
        "gold_qa_benchmark_adapter.py",
    ):
        p = app / "use_cases" / "evaluation" / name
        if p.exists():
            _move(p, orch / "evaluation" / name)

    for src, dst in (
        (app / "auth" / "dtos.py", dto / "auth.py"),
        (app / "projects" / "dtos.py", dto / "projects.py"),
        (app / "ingestion" / "dtos.py", dto / "ingestion.py"),
        (app / "settings" / "dtos.py", dto / "settings.py"),
        (app / "evaluation" / "dtos.py", dto / "evaluation.py"),
        (app / "evaluation" / "benchmark_export_dtos.py", dto / "benchmark_export.py"),
    ):
        if src.exists():
            _move(src, dst)

    rag_dto = app / "rag" / "dtos"
    if rag_dto.is_dir():
        dto_rag = dto / "rag"
        dto_rag.mkdir(parents=True, exist_ok=True)
        for p in rag_dto.iterdir():
            _move(p, dto_rag / p.name)
        rag_dto.rmdir()

    wire_py = app / "http" / "wire.py"
    if wire_py.exists():
        _move(wire_py, wire_pkg / "__init__.py")
    jw = app / "json_wire.py"
    if jw.exists():
        _move(jw, wire_pkg / "json_wire.py")

    fs = app / "frontend_support"
    if fs.is_dir():
        for p in fs.iterdir():
            _move(p, services / p.name)
        fs.rmdir()

    up = app / "users" / "avatar_upload_policy.py"
    if up.exists():
        _move(up, pol / "avatar_upload_policy.py")

    for name in (
        "retrieval_merge_default.py",
        "retrieval_preset_merge_port.py",
        "retrieval_settings_tuner.py",
    ):
        p = app / "settings" / name
        if p.exists():
            _move(p, services / name)

    ports = app / "ports"
    ports.mkdir(parents=True, exist_ok=True)
    ip = app / "auth" / "identity_ports.py"
    if ip.exists():
        _move(ip, ports / "identity_ports.py")

    _touch_init(dto)
    _touch_init(dto / "rag")
    _touch_init(orch / "rag")
    _touch_init(orch / "evaluation")
    _touch_init(wire_pkg)


def phase_infrastructure_flatten(api_src: Path) -> None:
    inf = api_src / "infrastructure"
    adapters = inf / "adapters"

    def move_ad(sub: str, dst: Path) -> None:
        src = adapters / sub
        if not src.exists():
            return
        dst.mkdir(parents=True, exist_ok=True)
        for p in src.iterdir():
            target = dst / p.name
            if target.exists():
                raise FileExistsError(target)
            shutil.move(str(p), str(dst / p.name))
        src.rmdir()

    def merge_adapters_into(sub: str, dst: Path) -> None:
        src = adapters / sub
        if not src.exists():
            return
        dst.mkdir(parents=True, exist_ok=True)
        for p in src.iterdir():
            target = dst / p.name
            if target.exists() and p.name == "__init__.py":
                continue
            if target.exists():
                raise FileExistsError(target)
            shutil.move(str(p), str(target))
        try:
            src.rmdir()
        except OSError:
            pass

    move_ad("auth", inf / "auth")
    move_ad("rag", inf / "rag")
    move_ad("evaluation", inf / "evaluation")
    merge_adapters_into("qa_dataset", inf / "evaluation")
    move_ad("filesystem", inf / "storage")
    move_ad("query_logging", inf / "observability")
    merge_adapters_into("document", inf / "rag")
    merge_adapters_into("workspace", inf / "persistence")

    sqlite_ad = adapters / "sqlite"
    psql = inf / "persistence" / "sqlite"
    psql.mkdir(parents=True, exist_ok=True)
    if sqlite_ad.exists():
        asset_src = sqlite_ad / "asset_repository.py"
        for p in list(sqlite_ad.iterdir()):
            if p.name in ("asset_repository.py", "__pycache__"):
                continue
            target = psql / p.name
            if target.exists() and p.name == "__init__.py":
                continue
            if target.exists():
                raise FileExistsError(target)
            shutil.move(str(p), str(target))
        if asset_src.exists():
            dst_asset = psql / "asset_repository.py"
            dst_asset.unlink(missing_ok=True)
            shutil.move(str(asset_src), str(dst_asset))
        for p in list(sqlite_ad.iterdir()):
            if p.is_file():
                p.unlink()
        try:
            sqlite_ad.rmdir()
        except OSError:
            pass

    for name in ("summary_recall_document_adapter.py",):
        p = adapters / name
        if p.exists():
            _move(p, inf / "rag" / name)

    if (inf / "vectorstores").exists():
        _merge_dir(inf / "vectorstores", inf / "rag" / "vectorstores")
    if (inf / "llm").exists():
        _merge_dir(inf / "llm", inf / "rag" / "llm")
    if (inf / "ingestion").exists():
        _merge_dir(inf / "ingestion", inf / "rag" / "ingestion")
    if (inf / "web").exists():
        _merge_dir(inf / "web", inf / "rag" / "web")
    if (inf / "logging").exists():
        _merge_dir(inf / "logging", inf / "observability" / "logging")
    if (inf / "caching").exists():
        _merge_dir(inf / "caching", inf / "persistence" / "caching")

    if adapters.exists():
        py_left = [
            p
            for p in adapters.rglob("*.py")
            if p.name != "__init__.py" and "__pycache__" not in p.parts
        ]
        if py_left:
            raise RuntimeError(f"adapters not empty: {py_left}")
        shutil.rmtree(adapters)


def phase_composition_auth_wiring(api_src: Path) -> None:
    comp = api_src / "composition"
    aw = comp / "auth_wiring.py"
    if not aw.exists():
        aw.write_text(
            '"""Auth-specific composition hooks (JWT, credentials)."""\n\n'
            "from __future__ import annotations\n",
            encoding="utf-8",
        )


def phase_frontend(root: Path, fe: Path, fe_src: Path, api_src: Path) -> None:
    fe.mkdir(parents=True, exist_ok=True)
    fe_src.mkdir(parents=True, exist_ok=True)
    for sub in ("state", "viewmodels", "utils"):
        _touch_init(fe_src / sub)
    _touch_init(fe_src / "components")
    for sub in ("chat", "projects"):
        _touch_init(fe_src / "components" / sub)

    _merge_dir(root / "pages", fe_src / "pages")
    _merge_dir(root / "src" / "ui", fe_src / "components" / "shared")
    _merge_dir(root / "src" / "frontend_gateway", fe_src / "services")
    _touch_init(fe_src / "pages")
    _touch_init(fe_src / "components" / "shared")
    _touch_init(fe_src / "services")

    guards_dst = fe_src / "utils" / "guards.py"
    g_src = root / "src" / "auth" / "guards.py"
    if not g_src.exists():
        g_src = api_src / "infrastructure" / "auth" / "guards.py"
    if g_src.exists():
        shutil.copy2(g_src, guards_dst)
    else:
        guards_dst.write_text(
            "import streamlit as st\n\ndef require_authentication(current_page: str) -> None:\n    return\n",
            encoding="utf-8",
        )

    (fe_src / "services" / "api_client.py").write_text(
        '"""Streamlit-facing backend client surface."""\n'
        "from __future__ import annotations\n\n"
        "from services.streamlit_api_client import StreamlitApiClient  # noqa: F401\n",
        encoding="utf-8",
    )

    app_py = fe / "app.py"
    root_stream = root / "streamlit_app.py"
    if root_stream.exists():
        text = root_stream.read_text(encoding="utf-8")
        text = text.replace("from src.ui.layout", "from components.shared.layout")
        text = text.replace("from src.auth.guards", "from utils.guards")
        app_py.write_text(text, encoding="utf-8")


def _relocate_tests_merge(src_dir: Path, dst_dir: Path) -> None:
    if not src_dir.exists():
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    for p in src_dir.iterdir():
        if p.name == "__pycache__":
            continue
        target = dst_dir / p.name
        if target.exists():
            raise FileExistsError(target)
        shutil.move(str(p), str(target))
    try:
        src_dir.rmdir()
    except OSError:
        pass


def phase_tests(root: Path, api: Path, fe: Path) -> None:
    root_tests = root / "tests"
    if not root_tests.exists():
        return
    dest = api / "tests"
    _rmtree(dest)
    shutil.move(str(root_tests), str(dest))

    (dest / "api").mkdir(parents=True, exist_ok=True)
    (dest / "e2e").mkdir(parents=True, exist_ok=True)

    for src_name, target in (
        ("composition", dest / "application"),
        ("domain", dest / "application"),
        ("apps_api", dest / "api"),
        ("infrastructure_services", dest / "infrastructure"),
        ("adapters", dest / "infrastructure"),
        ("auth", dest / "infrastructure"),
        ("core", dest / "infrastructure"),
        ("integration", dest / "e2e"),
        ("quality", dest / "e2e"),
    ):
        _relocate_tests_merge(dest / src_name, target)

    fe_tests = fe / "tests"
    fe_tests.mkdir(parents=True, exist_ok=True)
    _touch_init(fe_tests)
    for name in ("frontend_gateway", "ui"):
        src = dest / name
        if src.exists():
            dst = fe_tests / name
            if dst.exists():
                _rmtree(dst)
            shutil.move(str(src), str(dst))

    keep_top = {
        "architecture",
        "application",
        "infrastructure",
        "api",
        "e2e",
        "support",
        "fixtures",
    }
    leftovers = [p for p in dest.iterdir() if p.is_dir() and p.name not in keep_top]
    if leftovers:
        misc = dest / "application" / "_unclassified_tests"
        misc.mkdir(parents=True, exist_ok=True)
        for p in leftovers:
            shutil.move(str(p), str(misc / p.name))


def phase_api_main(api: Path) -> None:
    (api / "main.py").write_text(
        '"""API entry: python -m uvicorn api.main:app with repo root on PYTHONPATH."""\n'
        "from __future__ import annotations\n\n"
        "import sys\nfrom pathlib import Path\n\n"
        "_API_DIR = Path(__file__).resolve().parent\n"
        "_SRC = _API_DIR / \"src\"\n"
        "if str(_SRC) not in sys.path:\n    sys.path.insert(0, str(_SRC))\n\n"
        "from interfaces.http.main import create_app\n\n"
        "app = create_app()\n",
        encoding="utf-8",
    )
    init = api / "__init__.py"
    if not init.exists():
        init.write_text("", encoding="utf-8")


def phase_delete_old_roots(root: Path) -> None:
    _rmtree(root / "src")
    _rmtree(root / "apps")
    _rmtree(root / "pages")
    p = root / "streamlit_app.py"
    if p.exists():
        p.unlink()


def phase_root_scripts(root: Path) -> None:
    scripts = root / "scripts"
    (scripts / "validate_architecture.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nROOT=\"$(cd \"$(dirname \"$0\")/..\" && pwd)\"\n"
        "export PYTHONPATH=\"${ROOT}/api/src\"\n"
        "python -m pytest \"${ROOT}/api/tests/architecture\" -q \"$@\"\n",
        encoding="utf-8",
    )
    (scripts / "run_tests.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nROOT=\"$(cd \"$(dirname \"$0\")/..\" && pwd)\"\n"
        "export PYTHONPATH=\"${ROOT}/api/src:${ROOT}/frontend/src\"\n"
        "python -m pytest \"${ROOT}/api/tests\" \"${ROOT}/frontend/tests\" -q \"$@\"\n",
        encoding="utf-8",
    )
    (scripts / "lint.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nROOT=\"$(cd \"$(dirname \"$0\")/..\" && pwd)\"\n"
        "python -m ruff check \"${ROOT}/api/src\" \"${ROOT}/frontend/src\" \"$@\"\n",
        encoding="utf-8",
    )
