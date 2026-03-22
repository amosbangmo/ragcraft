# Streamlit and the backend client abstraction

## Goal

Streamlit pages and shared UI modules should depend on a small, stable **`BackendClient`** protocol (`src/frontend_gateway/protocol.py`), not on `RAGCraftApp` or the application container. That keeps the door open for:

- Serving the same features over **HTTP** (FastAPI or another API) with a thin **HTTP client** implementation.
- Replacing Streamlit with **Angular** (or another SPA) while reusing the same client interface.

## Current wiring

- **`get_backend_client()`** (`src/core/app_state.py`) returns **`InProcessBackendClient`**, which wraps the session singleton from **`get_app()`** (`RAGCraftApp`).
- **`render_page_header()`** exposes **`backend_client`** in its return dict; pages read `header["backend_client"]` and pass it into UI helpers or tab payloads (e.g. `"backend_client"` in evaluation tab dicts).

Behavior is unchanged from the previous direct façade calls: the in-process client is a thin delegate.

## Adding an HTTP implementation

1. **Implement `BackendClient`** in a new module, e.g. `src/frontend_gateway/http_client.py`, with methods that map 1:1 to existing REST routes (same DTO shapes as the API where possible).
2. **Authentication**: store API tokens or session cookies in Streamlit `st.session_state` (or headers on each request), matching how the API expects auth today.
3. **Swap the factory**: change `get_backend_client()` to return `HttpBackendClient(base_url=..., auth=...)` instead of `InProcessBackendClient(get_app())`, or branch on an env var (e.g. `RAGCRAFT_BACKEND_MODE=http`).
4. **Narrow surface over time**: methods that today expose `rag_service` / `evaluation_service` are oriented to in-process use. A remote client should prefer **dedicated API endpoints** (e.g. manual evaluation already has a use-case path); extend the protocol only when a page truly needs a new capability, and implement it on both in-process and HTTP sides.

## Page churn when switching to HTTP

Pages should only need **`get_backend_client()`** (or `header["backend_client"]`) to change implementation. They should **not** import `RAGCraftApp` for feature work. If a new screen needs a new operation, add it to **`BackendClient`** and implement it in **`InProcessBackendClient`** and the future **`HttpBackendClient`** together.

## Related

- `docs/migration/ragcraftapp-deprecation.md` — eventual removal of the Streamlit façade once all entrypoints use the client or HTTP only.
