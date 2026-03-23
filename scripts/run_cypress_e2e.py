#!/usr/bin/env python3
"""
Start uvicorn for E2E, run Cypress, write artifacts/cypress_run.log.

Exit code matches Cypress. Used by npm run cy:ci and generate_artifacts.py.
Cross-platform (avoids shell quoting issues with special paths on Windows).
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
LOG = ART / "cypress_run.log"


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
    raise RuntimeError(f"Server did not accept connections on {host}:{port}")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        default=None,
        help="Optional Cypress spec glob (default: all e2e specs).",
    )
    args = parser.parse_args()

    ART.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ragcraft_cypress_") as tmp:
        data_root = Path(tmp) / "data"
        env = _e2e_env(data_root=data_root)
        server = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "e2e_api_server.py")],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            _wait_port("127.0.0.1", 18976)
            try:
                argv = list(_cypress_run_argv())
                if args.spec:
                    argv.extend(["--spec", args.spec])
            except FileNotFoundError as exc:
                LOG.write_text(f"{exc}\n", encoding="utf-8")
                return 127
            try:
                cp = subprocess.run(
                    argv,
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=1200,
                )
            except subprocess.TimeoutExpired as exc:
                out = exc.stdout or ""
                err = exc.stderr or ""
                body = (
                    f"=== stdout ===\n{out}\n=== stderr ===\n{err}\n"
                    f"exit=timeout (Cypress subprocess > 1200s)\n"
                )
                LOG.write_text(body, encoding="utf-8")
                return 124
            body = (
                f"=== stdout ===\n{cp.stdout or ''}\n=== stderr ===\n{cp.stderr or ''}\nexit={cp.returncode}\n"
            )
            LOG.write_text(body, encoding="utf-8")
            return int(cp.returncode)
        finally:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
