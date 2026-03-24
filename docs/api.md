# HTTP API (FastAPI)

FastAPI app under **`api/src/interfaces/http/`** (routers, schemas, **`dependencies.py`**, upload helpers). **`create_app()`** builds the ASGI app; **`api/main.py`** exposes **`app`** for Uvicorn.

**Related:** **`docs/architecture.md`**, **`docs/testing_strategy.md`**, **`docs/product_features.md`**. **Smoke:** **`api/tests/bootstrap/`**, **`api/tests/reliability/test_app_boot.py`**. **Contracts:** **`api/tests/api/`**.

---

## 1. Run locally

Repository root; set **`PYTHONPATH`** so **`api.main`** resolves (or rely on **`scripts/run_tests`** / IDE config).

```bash
export PYTHONPATH="$(pwd)"   # Linux / macOS / Git Bash
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Set **`RAGCRAFT_JWT_SECRET`** before accepting real logins.

---

## 2. Authentication

1. **`POST /auth/login`** or **`POST /auth/register`** → JSON with **`access_token`**, **`token_type`** (`bearer`), **`user`** profile.
2. Scoped routes: header **`Authorization: Bearer <access_token>`** — e.g. **`/users/me`**, **`/projects`**, **`/chat/*`**, **`/evaluation/*`**.
3. Types: **`AuthenticatedPrincipal`**, **`AuthenticationPort`**, **`AccessTokenIssuerPort`** in **`api/src/domain/`**. **`interfaces/http/dependencies.py`** resolves auth from the composition root; handlers use **`AuthenticatedPrincipal`**, not raw infra types.
4. **Env:** **`RAGCRAFT_JWT_SECRET`** (required). Optional: **`RAGCRAFT_JWT_ISSUER`**, **`RAGCRAFT_JWT_AUDIENCE`**, **`RAGCRAFT_JWT_ALGORITHM`**, **`RAGCRAFT_ACCESS_TOKEN_EXPIRE_MINUTES`**.

---

## 3. Error envelope

JSON includes **`detail`**, **`message`**, **`error_type`**, **`code`**, **`category`**. Auth issues: **`401`** / **`400`** for malformed headers (see **`RAGCraftError`** handlers).

---

## 4. Multipart uploads

Bounded reads into **`BufferedDocumentUpload`** / avatar buffers — not unbounded streaming.

| Route | Field | Cap |
|-------|--------|-----|
| **`POST /projects/{project_id}/documents/ingest`** | **`file`** | **`RAG_MAX_UPLOAD_BYTES`** (~100 MiB default) |
| **`POST /users/me/avatar`** | **`file`** | **`RAG_MAX_AVATAR_UPLOAD_BYTES`** (~2 MiB) |

Oversized → **413**. Policy: **`api/src/application/ingestion/upload_boundary.py`**, **`interfaces/http/upload_adapter`**.

---

## 5. OpenAPI

**`/docs`**, **`/redoc`**, **`/openapi.json`**. **`BearerAuth`** in **`components.securitySchemes`**.

---

## 6. Route ownership

Routers only under **`api/src/interfaces/http/routers/`**. Handlers: validate → **`AuthenticatedPrincipal`** where needed → use case from container → Pydantic response (**`interfaces/http/schemas/`**). **No** **`infrastructure.*`** imports in routers.

---

## 7. API conventions

- **`project_id`** in JSON bodies: non-empty string; bad shape → **422**.
- **`project_id`** in paths: resource id; failures → documented **4xx/5xx**.
- **Bearer** on scoped routes; bad/missing token → **401** or **400**, not **5xx**.
- **Multipart** over limit → **413**.

**Feature ↔ route map:** **`docs/product_features.md`**.

---

## 8. Streamlit client (wire contract)

The UI must treat **HTTP JSON** as the contract, not **`application.dto`** / **`domain`** types in **`frontend/src`**. Streamlit page scripts live under **`frontend/pages/`** (next to **`app.py`**); they use the same façade imports as **`frontend/src/components/`**.

| Piece | Location | Role |
|-------|----------|------|
| **Public façade** | **`frontend/src/services/api_client.py`** | **Only** import for **`frontend/pages/`** / **`frontend/src/components/`**: **`BackendClient`**, **`get_backend_client`**, wire/view-model helpers, preset merge |
| **HTTP client impl.** | **`frontend/src/services/http_backend_client.py`** | Requests + JSON → **`services.api_contract_models`** / **`evaluation_wire_models`** (no **`domain`** on hot path) |
| **Wire DTOs** | **`frontend/src/services/api_contract_models.py`**, **`evaluation_wire_*`**, **`http_payloads.py`** | Match FastAPI JSON |

**Streamlit → API (HTTP only):** **`RAGCRAFT_API_BASE_URL`**, timeouts (**`RAGCRAFT_API_CONNECT_TIMEOUT_SECONDS`**, **`RAGCRAFT_API_READ_TIMEOUT_SECONDS`** / legacy **`RAGCRAFT_API_TIMEOUT_SECONDS`**). **`Authorization: Bearer`** from session — **`frontend/src/services/http_transport.py`**. Errors → **`BackendHttpError`** / **`RAGCraftError`** via **`services/http_error_map.py`**. There is **no** alternate transport or env switch for the UI.

---

## 9. Regression tests (pointer)

| Concern | Location |
|---------|----------|
| ASGI / **`api/main.py`** | **`api/tests/bootstrap/test_asgi_entrypoint.py`**, **`api/tests/reliability/test_app_boot.py`** |
| Routes, OpenAPI, pipelines | **`api/tests/api/`** (**`test_http_pipeline_e2e.py`**, …) |
| Auth + **`/users/me`** flow | **`api/tests/reliability/test_auth_flow.py`**, **`api/tests/api/test_auth_router.py`** |
