"""Browser E2E against a live uvicorn process (no route mocking)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e_browser


def test_openapi_docs_renders(live_api_url: str) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"{live_api_url}/docs", wait_until="domcontentloaded", timeout=60_000)
            title = page.title() or ""
            assert "RAGCraft" in title or "FastAPI" in title
        finally:
            browser.close()


def test_health_json(live_api_url: str) -> None:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"{live_api_url}/health", wait_until="domcontentloaded", timeout=60_000)
            body = page.inner_text("body")
            assert "ok" in body.lower() or "{" in body
        finally:
            browser.close()
