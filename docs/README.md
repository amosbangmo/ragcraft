# RAGCraft documentation

Concise, **code-aligned** documentation for the repository layout after the Clean Architecture and RAG orchestration migration.

| Document | Purpose |
|----------|---------|
| [architecture.md](architecture.md) | Layer responsibilities: domain, application, infrastructure, composition, API, gateway; RAG adapter import rules; **mermaid** dependency diagram |
| [api.md](api.md) | HTTP authentication (**Bearer JWT**), env vars, error envelope, OpenAPI pointers |
| [rag_orchestration.md](rag_orchestration.md) | RAG flow: entrypoints, use cases, orchestration modules, ports, adapters, logging, evaluation path |
| [dependency_rules.md](dependency_rules.md) | Allowed import directions, RAG-specific rules, anti-patterns |
| [testing_strategy.md](testing_strategy.md) | Architecture tests (including orchestration purity and RAG layering), integration coverage |
| [migration_report_final.md](migration_report_final.md) | **End-state** migration report: what was strong, what each hardening pass fixed, **structural guardrails**, **remaining risks**, final maturity verdict |
| [final_orchestration_gap_analysis.md](final_orchestration_gap_analysis.md) | Historical baseline → **closure** summary (orchestration gaps addressed); live flow in `rag_orchestration.md` |

**Also at repo root:** `ARCHITECTURE_TARGET.md` — short runtime layout and client modes; should stay aligned with `docs/architecture.md` and `docs/migration_report_final.md`.

**Tooling:** `pyproject.toml` configures **Ruff**, **Black**, **mypy**, and **pytest** defaults (see **`docs/architecture.md`** § Tooling). Runtime packages are listed in **`requirements.txt`**.

## Architecture validation (CI lock-in)

From repo root with **`PYTHONPATH=.`** (GitHub Actions sets this for pytest):

```bash
./scripts/validate.sh
```

Windows: **`.\scripts\validate.ps1`**

These run **Ruff** on **`src`**, **`apps`**, and **`tests/architecture`**, then **`pytest tests/architecture`**. **`.github/workflows/ci.yml`** runs the same checks on every push/PR (plus existing unittest jobs).

## Local development (Streamlit + FastAPI)

- Run API: `python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000` with `PYTHONPATH` set to the repo root and **`RAGCRAFT_JWT_SECRET`** set (see **`docs/api.md`**).
- Point Streamlit at the API: set `RAGCRAFT_BACKEND_CLIENT=http` and `RAGCRAFT_API_BASE_URL` (e.g. `http://127.0.0.1:8000`).
- In-process Streamlit (no uvicorn): `RAGCRAFT_BACKEND_CLIENT=in_process` uses `build_streamlit_backend_application_container()` (same use cases, `StreamlitChatTranscript` for session state).
- Optional: **`RAG_MAX_UPLOAD_BYTES`** / **`RAG_MAX_AVATAR_UPLOAD_BYTES`** — multipart caps (see `docs/migration_report_final.md` §12 and `docs/api.md`).
