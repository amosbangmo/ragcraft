#!/usr/bin/env python3
"""
Regenerate CI-like artifacts under repo-root artifacts/.

Usage (from repo root):
  python scripts/generate_artifacts.py

Requires: requirements.txt (pytest, pytest-cov) and npm deps (Cypress) for E2E logs.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"


def _env() -> dict[str, str]:
    e = os.environ.copy()
    sep = os.pathsep
    roots = [
        str(ROOT / "api" / "src"),
        str(ROOT / "frontend" / "src"),
        str(ROOT / "api" / "tests"),
    ]
    e["PYTHONPATH"] = sep.join(roots)
    e.setdefault("OPENAI_API_KEY", "ci-test-key")
    e.setdefault(
        "RAGCRAFT_JWT_SECRET",
        "ci-jwt-secret-at-least-32-characters-long!!",
    )
    return e


def run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = False,
    timeout_s: float | None = None,
    timeout_level: str | None = None,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    try:
        return subprocess.run(
            cmd,
            cwd=ROOT,
            env=_env(),
            check=check,
            text=True,
            capture_output=capture,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        label = timeout_level or "subprocess.run"
        msg = (
            f"[ragcraft-artifacts] TIMEOUT_LEVEL: {label} "
            f"(command wall_limit={timeout_s}s)\n  cmd: {' '.join(cmd)}"
        )
        print(msg, flush=True)
        print(msg, file=sys.stderr, flush=True)
        raise exc


def write_text(name: str, body: str) -> None:
    path = ART / name
    path.write_text(body.strip() + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}", flush=True)


def _clone_xml_element(el: ET.Element) -> ET.Element:
    return ET.fromstring(ET.tostring(el, encoding="utf-8"))


def split_cypress_junit_fragments() -> None:
    """Write rag_invariants_junit.xml and robustness_failure_handling_junit.xml from combined run."""
    src = ART / "cypress_junit.xml"
    if not src.is_file():
        return
    tree = ET.parse(src)
    root = tree.getroot()
    splits: list[tuple[str, Path]] = [
        ("rag_invariants.cy.js", ART / "rag_invariants_junit.xml"),
        ("robustness_failure.cy.js", ART / "robustness_failure_handling_junit.xml"),
    ]
    for fragment, dest in splits:
        wrapper = ET.Element("testsuites")
        wrapper.set("name", "Mocha Tests")
        matched = False
        for ts in root.findall("testsuite"):
            fp = (ts.get("file") or "").replace("\\", "/")
            if fragment not in fp:
                continue
            wrapper.append(_clone_xml_element(ts))
            matched = True
        if matched:
            ET.ElementTree(wrapper).write(dest, encoding="utf-8", xml_declaration=True)
            print(f"  wrote {dest.relative_to(ROOT)} (split from cypress_junit.xml)", flush=True)


def coverage_test_paths() -> list[str]:
    appli = ROOT / "api" / "tests" / "appli"
    domain = ROOT / "api" / "tests" / "domain"
    paths: list[str] = []
    if appli.is_dir():
        paths.append(str(appli))
    if domain.is_dir():
        paths.append(str(domain))
    if not paths:
        raise SystemExit("No api/tests/appli (or domain) directory for coverage.")
    return paths


def _extract_coverage_term_table(combined_output: str) -> str:
    """
    Pull the pytest-cov terminal table (Name / Stmts / Miss / Cover … TOTAL) from
    captured stdout+stderr.
    """
    lines = combined_output.replace("\r\n", "\n").split("\n")
    header_i: int | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("Name"):
            continue
        if "Stmts" not in line or "Miss" not in line or "Cover" not in line:
            continue
        header_i = i
        break
    if header_i is None:
        return combined_output.strip() or "(no coverage table in pytest output)"

    start = header_i
    if header_i > 0:
        prev = lines[header_i - 1].strip()
        if prev and set(prev) == {"-"}:
            start = header_i - 1

    total_i: int | None = None
    for j in range(header_i, len(lines)):
        if lines[j].strip().startswith("TOTAL"):
            total_i = j
            break
    if total_i is None:
        return "\n".join(lines[start:]).strip()

    end = total_i
    if total_i + 1 < len(lines):
        nxt = lines[total_i + 1].strip()
        if nxt and set(nxt) == {"-"}:
            end = total_i + 1

    chunk = lines[start : end + 1]
    for k in range(end + 1, min(end + 4, len(lines))):
        if "skipped due to complete coverage" in lines[k]:
            chunk.append(lines[k])
            break
    return "\n".join(chunk).rstrip()


def step_coverage() -> None:
    cov_xml = ART / "coverage.xml"
    cp = run(
        [
            sys.executable,
            "-m",
            "pytest",
            *coverage_test_paths(),
            "--cov=application",
            "--cov=domain",
            f"--cov-report=xml:{cov_xml}",
            "--cov-report=term:skip-covered",
            "-q",
            "--tb=no",
        ],
        capture=True,
    )
    if cp.stdout:
        sys.stdout.write(cp.stdout)
        if not cp.stdout.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
    if cp.stderr:
        sys.stderr.write(cp.stderr)
        if not cp.stderr.endswith("\n"):
            sys.stderr.write("\n")
        sys.stderr.flush()

    combined = (cp.stdout or "") + "\n" + (cp.stderr or "")
    term_table = _extract_coverage_term_table(combined)

    tree = ET.parse(cov_xml)
    root = tree.getroot()
    lv = root.get("lines-valid", "?")
    lc = root.get("lines-covered", "?")
    rate = root.get("line-rate", "?")
    try:
        pct = float(rate) * 100.0
        rate_human = f"{pct:.1f}%"
    except (TypeError, ValueError):
        rate_human = str(rate)
    note = ""
    if not (ROOT / "api" / "tests" / "domain").is_dir():
        note = (
            "\nNote: api/tests/domain is missing; coverage used api/tests/appli only "
            "(CI lists both paths when present).\n"
        )
    body = textwrap.dedent(
        f"""\
        RAGCraft — résumé couverture (pytest-cov)
        ==========================================

        Généré: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
        Fichier machine: coverage.xml (Cobertura)

        Globaux (packages application + domain)
        ---------------------------------------
        - Lignes couvertes: {lc} / {lv}
        - Taux de ligne (line-rate): {rate_human}
        {note}
        Détail par fichier (sortie --cov-report=term:skip-covered)
        ------------------------------------------------------------
        """
    ).strip()
    write_text(
        "COVERAGE_SUMMARY.txt",
        body + "\n\n" + term_table + "\n",
    )


def step_cypress() -> None:
    fail_hint = textwrap.dedent(
        """\
        ÉCHEC Cypress. Vérifiez Node/npm et installez les deps:
          npm ci
        Puis relancez. Sortie brute: cypress_run.log
        """
    )
    cp = run(
        [sys.executable, str(ROOT / "scripts" / "run_cypress_e2e.py")],
        check=False,
    )
    print("  (cypress) wrote artifacts/cypress_run.log", flush=True)
    if cp.returncode == 127:
        write_text(
            "CYPRESS_REPORT.txt",
            fail_hint + "\n(npx introuvable — installez Node.js)\n",
        )
        raise SystemExit("npx not found; install Node.js and run npm ci")
    if cp.returncode == 124:
        msg = (
            "[ragcraft-artifacts] Échec E2E: TIMEOUT_LEVEL=cypress_cli_subprocess "
            "(durée max Cypress dépassée; défaut 2400s, surcharger avec "
            "RAGCRAFT_CYPRESS_CLI_TIMEOUT_S). Voir la console et artifacts/cypress_run.log"
        )
        print(msg, flush=True)
        print(msg, file=sys.stderr, flush=True)
    elif cp.returncode == 125:
        msg = (
            "[ragcraft-artifacts] Échec E2E: TIMEOUT_LEVEL=e2e_api_server_listen "
            "(API 127.0.0.1:18976 pas prête en 60s). Voir artifacts/cypress_run.log"
        )
        print(msg, flush=True)
        print(msg, file=sys.stderr, flush=True)
    if cp.returncode != 0:
        write_text("CYPRESS_REPORT.txt", fail_hint)
        raise subprocess.CalledProcessError(
            cp.returncode,
            cp.args,
            cp.stdout,
            cp.stderr,
        )
    split_cypress_junit_fragments()
    write_text(
        "RAG_INVARIANTS.txt",
        textwrap.dedent(
            f"""\
            Rapport invariants RAG (Cypress)
            ================================

            Généré: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
            Spec: cypress/e2e/rag_invariants.cy.js (HTTP inspect/ask, latences, modes)
            JUnit dédié: rag_invariants_junit.xml (extrait de cypress_junit.xml)
            Suite complète: cypress_junit.xml
            Tests Python mockés historiques: api/tests/appli/rag/test_rag_pipeline_invariants.py
            """
        ),
    )
    write_text(
        "ROBUSTNESS_FAILURE_HANDLING.txt",
        textwrap.dedent(
            f"""\
            Rapport robustesse & échecs (Cypress)
            ======================================

            Généré: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
            Spec: cypress/e2e/robustness_failure.cy.js (422/401, rapport failures benchmark vide)
            JUnit dédié: robustness_failure_handling_junit.xml (extrait de cypress_junit.xml)
            Suite complète: cypress_junit.xml
            Tests unitaires historiques: api/tests/api/test_ingestion_robustness.py,
            api/tests/infra/test_failure_analysis_service.py
            """
        ),
    )
    write_text(
        "CYPRESS_REPORT.txt",
        textwrap.dedent(
            f"""\
            Rapport E2E navigateur (Cypress)
            =================================

            Généré: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
            Specs: cypress/e2e/*.cy.js (public_surface, workspace_journey, rag_invariants, robustness_failure)
            Logs: cypress_run.log
            JUnit agrégé: cypress_junit.xml
            Extraits: rag_invariants_junit.xml, robustness_failure_handling_junit.xml
            """
        ),
    )


def step_benchmark() -> None:
    code = """
import time
from unittest.mock import MagicMock
from application.use_cases.chat.ask_question import AskQuestionUseCase
from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult

pipeline = PipelineBuildResult()
retrieval = MagicMock()
retrieval.execute.return_value = pipeline
generation = MagicMock()
generation.generate_answer.return_value = "ok"
ask = AskQuestionUseCase(retrieval=retrieval, generation=generation, query_log=None)
project = Project(user_id="u", project_id="p")
runs = 200
t0 = time.perf_counter()
for _ in range(runs):
    ask.execute(project, "hello", [])
elapsed_ms = (time.perf_counter() - t0) * 1000.0
print(f"mini_benchmark_ask_question_mocked: {runs} runs, total_ms={elapsed_ms:.3f}, per_call_ms={elapsed_ms/runs:.4f}")
"""
    cp = run([sys.executable, "-c", code], capture=True)
    line = (cp.stdout or "").strip().splitlines()[-1] if cp.stdout else "(no output)"
    write_text(
        "BENCHMARK_RUNTIME.txt",
        textwrap.dedent(
            f"""\
            Mini benchmark runtime
            =======================

            Généré: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

            {line}

            Le test pytest api/tests/appli/test_performance_smoke.py borne un seul appel
            mocké à < 500 ms (smoke).

            Les durées de suite complète dépendent de la machine; voir sortie pytest
            pour les étapes ci-dessous.
            """
        ),
    )


def step_ci_log() -> None:
    chunks: list[str] = []
    chunks.append(
        f"=== CI local equivalent (UTF-8) {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} ===\n"
        f"ROOT: {ROOT}\n"
    )

    def append_title(t: str) -> None:
        chunks.append(f"\n=== {t} ===\n")

    append_title("ruff check . --select E9,F63,F7,F82")
    try:
        cp = run(
            [sys.executable, "-m", "ruff", "check", ".", "--select", "E9,F63,F7,F82"],
            capture=True,
            check=False,
        )
        chunks.append(cp.stdout or "")
        chunks.append(cp.stderr or "")
        if cp.returncode != 0:
            chunks.append(f"(exit {cp.returncode})\n")
    except FileNotFoundError:
        chunks.append("(ruff not installed — pip install ruff)\n")

    append_title("pytest api/tests/architecture api/tests/bootstrap -q --tb=short")
    cp = run(
        [
            sys.executable,
            "-m",
            "pytest",
            "api/tests/architecture",
            "api/tests/bootstrap",
            "-q",
            "--tb=short",
        ],
        capture=True,
    )
    chunks.append(cp.stdout or "")
    chunks.append(cp.stderr or "")

    append_title(
        "pytest api/tests (no arch/bootstrap) + frontend/tests -q --tb=short"
    )
    cp = run(
        [
            sys.executable,
            "-m",
            "pytest",
            "api/tests",
            "--ignore=api/tests/architecture",
            "--ignore=api/tests/bootstrap",
            "frontend/tests",
            "-q",
            "--tb=short",
        ],
        capture=True,
    )
    chunks.append(cp.stdout or "")
    chunks.append(cp.stderr or "")

    chunks.append(
        textwrap.dedent(
            """

            === Non inclus ici (voir .github/workflows/ci.yml) ===
            - bash scripts/lint.sh
            - npm ci + Cypress E2E (généré séparément → cypress_run.log)
            - Couverture appli/domain (générée séparément → coverage.xml)
            - unittest discover (infra, integration, quality)
            - create_app() boot one-liner
            """
        )
    )
    write_text("ci_local_equivalent.txt", "".join(chunks))
    write_text(
        "CI_LOCAL_EQUIVALENT_README.txt",
        textwrap.dedent(
            f"""\
            Sortie CI équivalente locale
            ============================

            Généré: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

            ci_local_equivalent.txt résume des étapes proches de la CI (ruff critique,
            pytest architecture/bootstrap, pytest principal + frontend).

            Les logs GitHub Actions officiels restent sur l’onglet Actions du dépôt.
            """
        ),
    )


def main() -> None:
    ART.mkdir(parents=True, exist_ok=True)
    print("Artifacts dir:", ART, flush=True)
    step_coverage()
    step_benchmark()
    print(
        "[ragcraft-artifacts] Mini-benchmark terminé (BENCHMARK_RUNTIME.txt). "
        "Étape suivante: Cypress E2E (sortie en direct + artifacts/cypress_run.log)…",
        flush=True,
    )
    step_cypress()
    step_ci_log()
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
