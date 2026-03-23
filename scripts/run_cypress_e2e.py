#!/usr/bin/env python3
"""
Start uvicorn for E2E, run Cypress, write artifacts/cypress_run.log.

Exit code: Cypress return code, or 124 (Cypress wall-clock exceeded; see
``RAGCRAFT_CYPRESS_CLI_TIMEOUT_S``),
125 (API never listened on 127.0.0.1:18976 within 60s), 127 (node/Cypress missing).

On timeout, prints ``[ragcraft-artifacts] TIMEOUT_LEVEL: …`` to stdout and stderr.

Used by npm run cy:ci and generate_artifacts.py. Cross-platform (avoids shell
quoting issues with special paths on Windows).
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
LOG = ART / "cypress_run.log"


def _log_timeout_level(msg: str) -> None:
    """Emit timeout diagnostics on stdout and stderr (some runners only show one stream)."""
    print(msg, flush=True)
    print(msg, file=sys.stderr, flush=True)


def _cypress_run_argv() -> list[str]:
    """Avoid node_modules/.bin/*.cmd on Windows — paths with & break cmd.exe batch stubs."""
    node = shutil.which("node")
    if not node:
        raise FileNotFoundError("node not on PATH; install Node.js")
    cli = ROOT / "node_modules" / "cypress" / "bin" / "cypress"
    if not cli.is_file():
        raise FileNotFoundError(f"Cypress CLI missing at {cli}; run npm ci")
    return [node, str(cli), "run"]


def _e2e_env(*, data_root: Path | None = None) -> dict[str, str]:
    e = os.environ.copy()
    sep = os.pathsep
    e["PYTHONPATH"] = sep.join(
        str(p)
        for p in (
            ROOT / "api" / "src",
            ROOT / "frontend" / "src",
            ROOT / "api" / "tests",
        )
    )
    e.setdefault("OPENAI_API_KEY", "ci-test-key")
    e.setdefault(
        "RAGCRAFT_JWT_SECRET",
        "ci-jwt-secret-at-least-32-characters-long!!",
    )
    # CI placeholder key: cap OpenAI waits and skip query-rewrite LLM to keep HTTP E2E bounded.
    if e.get("OPENAI_API_KEY", "").strip() == "ci-test-key":
        e.setdefault("OPENAI_REQUEST_TIMEOUT_S", "45")
        e.setdefault("RAG_ENABLE_QUERY_REWRITE", "false")
        # Faster PDF path for E2E (unstructured); root LLM/embeddings are stubbed in config for this key.
        e.setdefault("RAG_PDF_STRATEGY_DEFAULT", "fast")
        e.setdefault("RAG_PDF_STRATEGY_FALLBACK", "fast")
        e.setdefault("RAG_ENABLE_PDF_IMAGE_EXTRACTION", "false")
        e.setdefault("RAG_ENABLE_PDF_OCR_FALLBACK", "false")
    if "CYPRESS_JUNIT_FILE" not in e:
        e["CYPRESS_JUNIT_FILE"] = str((ROOT / "artifacts" / "cypress_junit.xml").resolve())
    if data_root is not None:
        data_root.mkdir(parents=True, exist_ok=True)
        e["RAGCRAFT_DATA_PATH"] = str(data_root.resolve())
    return e


def _wait_port(host: str, port: int, timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.15)
    _log_timeout_level(
        "[ragcraft-artifacts] TIMEOUT_LEVEL: e2e_api_server_listen "
        f"(polling TCP connect to {host}:{port}, wall_limit={timeout_s}s)"
    )
    raise RuntimeError(
        f"Server did not accept connections on {host}:{port} within {timeout_s}s"
    )


def _cypress_cli_timeout_s() -> float:
    raw = os.environ.get("RAGCRAFT_CYPRESS_CLI_TIMEOUT_S", "2400")
    try:
        v = float(raw.strip())
    except ValueError:
        return 2400.0
    return max(300.0, v)


def _run_cypress_streaming(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log_path: Path,
    timeout_s: float,
) -> int:
    """
    Run Cypress with stdout/stderr merged, line-copy to log file and process stdout
    (so generate_artifacts / CI show live progress).
    """
    header = (
        f"=== ragcraft run_cypress_e2e {datetime.now(timezone.utc).isoformat()} UTC ===\n"
        f"timeout_s={timeout_s}\n"
        f"argv: {argv}\n\n"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(header, encoding="utf-8")
    proc = subprocess.Popen(
        argv,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert proc.stdout is not None

    with open(log_path, "a", encoding="utf-8", errors="replace") as logf:

        def _pump() -> None:
            try:
                for line in iter(proc.stdout.readline, ""):
                    if not line:
                        break
                    logf.write(line)
                    logf.flush()
                    sys.stdout.write(line)
                    sys.stdout.flush()
            except Exception:
                pass

        pump = threading.Thread(target=_pump, daemon=True)
        pump.start()
        try:
            rc = proc.wait(timeout=timeout_s)
            pump.join(timeout=60)
            logf.write(f"\n=== exit={rc} ===\n")
            logf.flush()
            return int(rc) if rc is not None else 1
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
            pump.join(timeout=15)
            logf.write(f"\n=== exit=timeout (>{timeout_s}s) ===\n")
            logf.flush()
            raise


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        default=None,
        help="Optional Cypress spec glob (default: all e2e specs).",
    )
    args = parser.parse_args()
    cy_timeout = _cypress_cli_timeout_s()

    ART.mkdir(parents=True, exist_ok=True)
    print(
        f"[ragcraft-e2e] Démarrage (Cypress CLI timeout={cy_timeout}s, "
        f"RAGCRAFT_CYPRESS_CLI_TIMEOUT_S pour surcharger)",
        flush=True,
    )
    with tempfile.TemporaryDirectory(prefix="ragcraft_cypress_") as tmp:
        data_root = Path(tmp) / "data"
        env = _e2e_env(data_root=data_root)
        print("[ragcraft-e2e] Lancement du serveur API E2E (uvicorn)…", flush=True)
        server = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "e2e_api_server.py")],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        streamlit_proc: subprocess.Popen | None = None
        try:
            try:
                _wait_port("127.0.0.1", 18976)
            except RuntimeError as exc:
                LOG.write_text(f"{exc}\n", encoding="utf-8")
                return 125
            env["RAGCRAFT_API_BASE_URL"] = "http://127.0.0.1:18976"
            streamlit_port = 18975
            if os.environ.get("RAGCRAFT_CYPRESS_SKIP_STREAMLIT", "").strip().lower() not in (
                "1",
                "true",
                "yes",
            ):
                print(
                    f"[ragcraft-e2e] Lancement Streamlit (127.0.0.1:{streamlit_port}) → API…",
                    flush=True,
                )
                streamlit_proc = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "streamlit",
                        "run",
                        str(ROOT / "frontend" / "app.py"),
                        "--server.port",
                        str(streamlit_port),
                        "--server.address",
                        "127.0.0.1",
                        "--server.headless",
                        "true",
                        "--browser.gatherUsageStats",
                        "false",
                    ],
                    cwd=str(ROOT),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                try:
                    _wait_port("127.0.0.1", streamlit_port, timeout_s=120.0)
                except RuntimeError as exc:
                    LOG.write_text(f"Streamlit failed to listen: {exc}\n", encoding="utf-8")
                    streamlit_proc.terminate()
                    try:
                        streamlit_proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        streamlit_proc.kill()
                    return 125
                env["CYPRESS_STREAMLIT_ORIGIN"] = f"http://127.0.0.1:{streamlit_port}"
            print(
                "[ragcraft-e2e] API prête sur 127.0.0.1:18976 — lancement de Cypress…",
                flush=True,
            )
            try:
                argv = list(_cypress_run_argv())
                if args.spec:
                    argv.extend(["--spec", args.spec])
            except FileNotFoundError as exc:
                LOG.write_text(f"{exc}\n", encoding="utf-8")
                return 127
            print(f"[ragcraft-e2e] Commande: {' '.join(argv)}", flush=True)
            try:
                return _run_cypress_streaming(
                    argv,
                    cwd=ROOT,
                    env=env,
                    log_path=LOG,
                    timeout_s=cy_timeout,
                )
            except subprocess.TimeoutExpired:
                _log_timeout_level(
                    "[ragcraft-artifacts] TIMEOUT_LEVEL: cypress_cli_subprocess "
                    f"(subprocess waiting for Cypress CLI, wall_limit={cy_timeout}s)"
                )
                return 124
        finally:
            if streamlit_proc is not None:
                streamlit_proc.terminate()
                try:
                    streamlit_proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    streamlit_proc.kill()
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                _log_timeout_level(
                    "[ragcraft-artifacts] TIMEOUT_LEVEL: e2e_api_server_shutdown "
                    "(Popen.wait after terminate, wall_limit=15s) — sending kill"
                )
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
