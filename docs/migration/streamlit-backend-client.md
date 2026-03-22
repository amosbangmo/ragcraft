# Streamlit and the backend client abstraction

## Goal

Streamlit pages and shared UI modules should depend on a small, stable **`BackendClient`** protocol (`src/frontend_gateway/protocol.py`), not on `RAGCraftApp` or the application container. That keeps the door open for:

- Serving the same features over **HTTP** (FastAPI or another API) with a thin **HTTP client** implementation.
- Replacing Streamlit with **Angular** (or another SPA) while reusing the same client interface.

## Current wiring

- **`get_backend_client()`** (`src/core/app_state.py`) returns:
  - **`InProcessBackendClient`** (default) — wraps **`get_app()`** (`RAGCraftApp`).
  - **`HttpBackendClient`** when **`RAGCRAFT_BACKEND_CLIENT=http`** — calls FastAPI with **`httpx`** and sends **`X-User-Id`** on every request that requires it.
- **`render_page_header()`** exposes **`backend_client`** in its return dict; pages read `header["backend_client"]` and pass it into UI helpers or tab payloads (e.g. `"backend_client"` in evaluation tab dicts).

Runbook for API vs in-process Streamlit: **`docs/migration/streamlit-fastapi-dev.md`**.

## HTTP implementation (done)

- **`src/frontend_gateway/http_client.py`** — maps protocol methods to existing routes; errors are mapped to **`BackendHttpError`** or **`RAGCraftError`** subclasses when the API returns matching **`error_type`** (e.g. `VectorStoreError`).
- **Settings**: `src/frontend_gateway/settings.py` (`RAGCRAFT_API_BASE_URL`, `RAGCRAFT_API_TIMEOUT_SECONDS`).
- **Chat transcript** still uses local **`ChatService`** in HTTP mode; RAG turns go to **`POST /chat/ask`**.

## Adding more remote surface

1. Add or extend a FastAPI route (use cases + `Depends` only in routers; DB init via **`apps.api.dependencies`**, not inside router modules — see architecture tests).
2. Add the matching method on **`HttpBackendClient`** and **`InProcessBackendClient`**.
3. Prefer **dedicated REST** over exposing **`rag_service`** / **`evaluation_service`** on the HTTP client (those remain **unsupported** stubs over HTTP).

## Page churn when switching to HTTP

Pages should only need **`get_backend_client()`** (or `header["backend_client"]`) to change implementation. They should **not** import `RAGCraftApp` for feature work. If a new screen needs a new operation, add it to **`BackendClient`** and implement it in **`InProcessBackendClient`** and the future **`HttpBackendClient`** together.

## Related

- `docs/migration/streamlit-fastapi-dev.md` — how to run Streamlit with FastAPI (in-process vs HTTP).
- `docs/migration/ragcraftapp-deprecation.md` — eventual removal of the Streamlit façade once all entrypoints use the client or HTTP only.
