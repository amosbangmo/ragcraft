# RAGCraft documentation

Concise, **code-aligned** documentation for the repository layout after the Clean Architecture and RAG orchestration migration.

| Document | Purpose |
|----------|---------|
| [architecture.md](architecture.md) | Layer responsibilities: domain, application, infrastructure, composition, API, gateway; RAG adapter import rules; **mermaid** dependency diagram |
| [rag_orchestration.md](rag_orchestration.md) | RAG flow: entrypoints, use cases, orchestration modules, ports, adapters, logging, evaluation path |
| [dependency_rules.md](dependency_rules.md) | Allowed import directions, RAG-specific rules, anti-patterns |
| [testing_strategy.md](testing_strategy.md) | Architecture tests (including orchestration purity and RAG layering), integration coverage |
| [migration_report_final.md](migration_report_final.md) | **End-state** migration report: current architecture, removed components, **remaining risks**, final verdict |
| [final_orchestration_gap_analysis.md](final_orchestration_gap_analysis.md) | Historical baseline → **closure** summary (orchestration gaps addressed); live flow in `rag_orchestration.md` |

**Also at repo root:** `ARCHITECTURE_TARGET.md` — short runtime layout and client modes; should stay aligned with `docs/architecture.md` and `docs/migration_report_final.md`.

## Local development (Streamlit + FastAPI)

- Run API: `python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000` with `PYTHONPATH` set to the repo root.
- Point Streamlit at the API: set `RAGCRAFT_BACKEND_CLIENT=http` and `RAGCRAFT_API_BASE_URL` (e.g. `http://127.0.0.1:8000`).
- In-process Streamlit (no uvicorn): `RAGCRAFT_BACKEND_CLIENT=in_process` uses `build_streamlit_backend_application_container()` (same use cases, `StreamlitChatTranscript` for session state).
- Optional: **`RAG_MAX_UPLOAD_BYTES`** caps multipart document upload size on the API (see `docs/migration_report_final.md` §11).
