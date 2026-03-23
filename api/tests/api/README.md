# HTTP / FastAPI contract tests

Pytest tests for **`interfaces.http`** (routers, dependencies, OpenAPI, upload adapter).

Shared helpers (e.g. **`bearer_auth`**) are imported as **`from api.bearer_auth import …`**. That works when **`PYTHONPATH`** includes **`api/tests`** **before** the repository root — as set by **`scripts/run_tests.sh`** / **`scripts/run_tests.ps1`** and root **`pyproject.toml`** **`[tool.pytest.ini_options] pythonpath`**.

Do **not** confuse this package with the ASGI package at the repository root (**`api/main.py`**, **`uvicorn api.main:app`**), which requires the **repository root** on **`PYTHONPATH`**, not the test tree. Entrypoint smoke tests live in **`api/tests/bootstrap/`** (run via **`scripts/validate_architecture.*`**).
