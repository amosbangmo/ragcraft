"""Live HTTP server for browser E2E (Playwright) against the real ASGI app."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _wait_port(host: str, port: int, timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.15)
    raise RuntimeError(f"Server did not accept connections on {host}:{port}")


@pytest.fixture(scope="session")
def live_api_url() -> Iterator[str]:
    pytest.importorskip("playwright")
    host = "127.0.0.1"
    port = 18976
    env = os.environ.copy()
    api_src = str(REPO_ROOT / "api" / "src")
    fe_src = str(REPO_ROOT / "frontend" / "src")
    roots = env.get("PYTHONPATH", "")
    extra = f"{api_src}{os.pathsep}{fe_src}"
    env["PYTHONPATH"] = f"{extra}{os.pathsep}{roots}" if roots else extra
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "interfaces.http.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(
        cmd,
        env=env,
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_port(host, port)
        yield f"http://{host}:{port}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
