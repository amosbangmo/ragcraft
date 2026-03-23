# RAGCraft API (FastAPI)

Python package root: `api/src/` (add to `PYTHONPATH` or run tools from repo root per `pyproject.toml`).

- Entry: `api/main.py` → `uvicorn api.main:app` with repository root on `PYTHONPATH`.
- HTTP delivery: `api/src/interfaces/http/`
- Domain / application / infrastructure / composition live under `api/src/` as top-level packages.
