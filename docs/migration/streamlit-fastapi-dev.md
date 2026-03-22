# Running Streamlit with FastAPI (in-process vs HTTP backend)

## Modes

| Mode | `RAGCRAFT_BACKEND_CLIENT` | What calls use cases |
|------|---------------------------|----------------------|
| **In-process** (default) | unset or `in_process` | `RAGCraftApp` in the Streamlit process |
| **HTTP** | `http` | FastAPI server; Streamlit uses `httpx` + `X-User-Id` |

Chat transcript stays in **Streamlit `session_state`** in both modes (`ChatService`). RAG, ingestion, evaluation, and projects go through the backend client (`get_backend_client()`).

## 1. FastAPI + Streamlit — in-process backend

Typical local dev: one process for Streamlit only; no API required.

```powershell
# From repo root (Windows PowerShell)
$env:PYTHONPATH = (Get-Location).Path
streamlit run streamlit_app.py
```

Optional: run the API in parallel for manual checks (`/docs`) while Streamlit still uses in-process mode:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

Do **not** set `RAGCRAFT_BACKEND_CLIENT=http` if you want Streamlit to ignore the API.

## 2. FastAPI + Streamlit — HTTP backend

Use two terminals. **Same** `PYTHONPATH` and **same** data root (default layout under the repo) so SQLite and `users/` directories match.

**Terminal A — API**

```powershell
cd <repo-root>
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal B — Streamlit**

```powershell
cd <repo-root>
$env:PYTHONPATH = (Get-Location).Path
$env:RAGCRAFT_BACKEND_CLIENT = "http"
$env:RAGCRAFT_API_BASE_URL = "http://127.0.0.1:8000"
streamlit run streamlit_app.py
```

Optional tuning:

- `RAGCRAFT_API_TIMEOUT_SECONDS` — default `300` (large dataset evaluations may need more).

### Identity header

Every mutating/listing API call from `HttpBackendClient` sends **`X-User-Id`** set to the current Streamlit session user (authenticated `user_id` or anonymous id). Routes that also take `user_id` in the JSON body (e.g. `/chat/ask`) **must** use the same value; the client sets both to match.

### After profile changes over HTTP

The profile page calls `AuthService.refresh_session_from_user_id` after successful API-backed updates so the sidebar username/avatar stay in sync with SQLite.

## Related

- `docs/migration/streamlit-backend-client.md` — protocol and swapping implementations.
- `apps/api/main.py` — OpenAPI at `/docs`.
