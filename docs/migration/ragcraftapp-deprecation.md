# RAGCraftApp — in-process adapter (not the FastAPI root)

FastAPI uses **`BackendApplicationContainer`** via `apps/api/dependencies.py`. **`RAGCraftApp`** (`src/app/ragcraft_app.py`) is **not** obsolete: it is the **supported in-process adapter** used by **`InProcessBackendClient`** so Streamlit can run without uvicorn while reusing the same container and use cases as the HTTP API.

## Responsibilities

- Hold a **`BackendApplicationContainer`** built with `build_backend(...)`.
- Expose the same service surface the protocol expects (chat, RAG, evaluation, projects, etc.).
- Apply **Streamlit-only** concerns where needed (e.g. session chain cache invalidation alongside the process-wide cache).

## What not to do

- Do not wire **FastAPI** through `RAGCraftApp` (that path was removed).
- Do not import **`src.app`** from new **`pages/`** or **`src/ui/`** code — use **`get_backend_client()`** / **`BackendClient`** instead.

See **`ARCHITECTURE_TARGET.md`** and **`final-status.md`** for the full runtime model.
