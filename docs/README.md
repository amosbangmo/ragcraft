# RAGCraft documentation

Concise, code-aligned documentation for the repository layout after the Clean Architecture migration.

| Document | Purpose |
|----------|---------|
| [architecture.md](architecture.md) | Layer responsibilities: domain, application, infrastructure, composition, API, gateway |
| [rag_orchestration.md](rag_orchestration.md) | RAG flow: entrypoints, use cases, ports, adapters, logging, answer generation |
| [dependency_rules.md](dependency_rules.md) | Allowed import directions and anti-patterns |
| [testing_strategy.md](testing_strategy.md) | Architecture tests and integration coverage |
| [migration_report_final.md](migration_report_final.md) | Final migration report (what changed, debt, next steps) |

**Also at repo root:** `ARCHITECTURE_TARGET.md` — short runtime layout and client modes; kept for quick reference and should stay aligned with `docs/architecture.md`.

## Local development (Streamlit + FastAPI)

- Run API: `python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000` with `PYTHONPATH` set to the repo root.
- Point Streamlit at the API: set `RAGCRAFT_BACKEND_CLIENT=http` and `RAGCRAFT_API_BASE_URL` (e.g. `http://127.0.0.1:8000`).
- In-process Streamlit (no uvicorn): `RAGCRAFT_BACKEND_CLIENT=in_process` uses `build_streamlit_backend_application_container()` (same use cases, `StreamlitChatTranscript` for session state).
