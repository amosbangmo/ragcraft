# Historical note — `RAGCraftApp` (removed)

The former **`RAGCraftApp`** façade (`src/app/ragcraft_app.py`) has been **removed** from the runtime.

**Today:**

- **FastAPI** uses **`BackendApplicationContainer`** via `apps/api/dependencies.py`.
- **Streamlit in-process mode** uses **`InProcessBackendClient`**, which holds a **`BackendApplicationContainer`** built by `src/frontend_gateway/streamlit_backend_factory.py` (same graph as production composition).

Do not reintroduce a monolithic app type; add behavior as **use cases** and wire them in **`src/composition/`**.

Canonical description: **`ARCHITECTURE_TARGET.md`**.
