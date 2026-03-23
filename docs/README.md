# RAGCraft documentation

**Layout note:** backend code lives under **`api/src/`**; Streamlit UI under **`frontend/src/`**; tests under **`api/tests/`** and **`frontend/tests/`**. Older path mentions (`src/…`, `apps/api/`) in the docs below are being aligned to this tree; see **`docs/migration_report_final.md`** for the authoritative physical layout.

Concise, **code-aligned** documentation for the repository layout after the Clean Architecture and RAG orchestration migration.

| Document | Purpose |
|----------|---------|
| [architecture.md](architecture.md) | Layer responsibilities: domain, application, infrastructure, composition, API, gateway; RAG adapter import rules; **mermaid** dependency diagram |
| [api.md](api.md) | HTTP authentication (**Bearer JWT**), env vars, error envelope, OpenAPI pointers |
| [rag_orchestration.md](rag_orchestration.md) | RAG flow: entrypoints, use cases, orchestration modules, ports, adapters, logging, evaluation path |
| [dependency_rules.md](dependency_rules.md) | Allowed import directions, RAG-specific rules, anti-patterns |
| [testing_strategy.md](testing_strategy.md) | How to run architecture validation, full tests, lint; architecture test index |
| [migration_report_final.md](migration_report_final.md) | **End-state** migration report: what was strong, what each hardening pass fixed, **structural guardrails**, **remaining risks**, final maturity verdict |
**Tooling:** root **`pyproject.toml`** configures **Ruff**, **Black**, **mypy**, and **pytest** defaults. Runtime packages are listed in **`requirements.txt`**.

## Architecture validation (first-class commands)

Structural and import drift is caught by **`api/tests/architecture/`**. Use the repo scripts from the **repository root** (same commands **CI** uses for lint + architecture + non-architecture pytest):

| Command | What it runs |
|---------|----------------|
| **`./scripts/validate_architecture.sh`** | **Pytest** — `api/tests/architecture` only (blocking). |
| **`./scripts/validate.sh`** | **`./scripts/lint.sh`** then **`./scripts/validate_architecture.sh`** (quick CI-style check). |
| **`./scripts/run_tests.sh`** | Architecture tests, then **`pytest api/tests`** with **`--ignore=api/tests/architecture`** plus **`frontend/tests`** (no duplicate architecture run). |
| **`./scripts/lint.sh`** | **Ruff** on **`api/src`**, **`frontend/src`**, **`api/tests/architecture`**. |

**Windows (PowerShell):** `.\scripts\validate_architecture.ps1`, `.\scripts\validate.ps1`, `.\scripts\run_tests.ps1`, `.\scripts\lint.ps1`.

**Manual equivalent** (any shell, repo root):

```bash
export PYTHONPATH=api/src:frontend/src:api/tests
python -m pytest api/tests/architecture -q
```

**Optional:** from **`api/`**, `pytest` runs only **`tests/architecture`** per **`api/pyproject.toml`**.

## Local development (Streamlit + FastAPI)

- Run API: `python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000` with **`PYTHONPATH`** including the **repository root** (so `api` is importable) and **`RAGCRAFT_JWT_SECRET`** set (see **`docs/api.md`**).
- Point Streamlit at the API: set `RAGCRAFT_BACKEND_CLIENT=http` and `RAGCRAFT_API_BASE_URL` (e.g. `http://127.0.0.1:8000`).
- In-process Streamlit (no uvicorn): `RAGCRAFT_BACKEND_CLIENT=in_process` uses `build_streamlit_backend_application_container()` (same use cases, `StreamlitChatTranscript` for session state).
- Optional: **`RAG_MAX_UPLOAD_BYTES`** / **`RAG_MAX_AVATAR_UPLOAD_BYTES`** — multipart caps (see `docs/migration_report_final.md` §12 and `docs/api.md`).
