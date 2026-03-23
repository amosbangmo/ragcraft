#!/usr/bin/env python3
"""Run uvicorn for browser E2E (Cypress). Blocks until killed; same layout as former Playwright conftest."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sep = os.pathsep
os.environ["PYTHONPATH"] = sep.join(
    str(p)
    for p in (
        ROOT / "api" / "src",
        ROOT / "frontend" / "src",
        ROOT / "api" / "tests",
    )
)
os.environ.setdefault("OPENAI_API_KEY", "ci-test-key")
os.environ.setdefault(
    "RAGCRAFT_JWT_SECRET",
    "ci-jwt-secret-at-least-32-characters-long!!",
)

import uvicorn

uvicorn.run(
    "interfaces.http.main:app",
    host="127.0.0.1",
    port=18976,
    log_level="warning",
)
