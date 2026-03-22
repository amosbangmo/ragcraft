# Retrieval settings as a backend contract

## Ownership

- **Persisted preferences** — `ProjectSettings` (preset key, `retrieval_advanced`, rewrite/hybrid flags) stored via `ProjectSettingsRepositoryPort` (`ProjectSettingsService` / SQLite).
- **Effective tuning** — `RetrievalSettings` (full retrieval surface including k values) derived by `RetrievalSettingsService` from presets and optional advanced overrides. Preset semantics live in `RetrievalSettingsService.from_preset` (unchanged).

## Application use cases (`src/application/settings`)

| Use case | Input | Output |
|----------|--------|--------|
| `GetEffectiveRetrievalSettingsUseCase` | `GetEffectiveRetrievalSettingsQuery` | `EffectiveRetrievalSettingsView` (`preferences`, `effective_retrieval`) |
| `UpdateProjectRetrievalSettingsUseCase` | `UpdateProjectRetrievalSettingsCommand` | Saved `ProjectSettings` (preset normalized via `parse_retrieval_preset`) |

Composition: `BackendApplicationContainer.settings_get_effective_retrieval_use_case` and `settings_update_project_retrieval_use_case`.  
`BackendComposition` exposes a **single** `retrieval_settings_service` instance (shared with the RAG retrieval subgraph built in the application container) so chat/search and settings use cases stay aligned.

## HTTP API

- `GET /projects/{project_id}/retrieval-settings` — JSON with `preferences` and `effective_retrieval` (dataclass `asdict` shapes).
- `PUT /projects/{project_id}/retrieval-settings` — body: `UpdateProjectRetrievalSettingsRequest`; response same as GET.

Identity: `X-User-Id` header (same as other project routes).

## Streamlit

`src/ui/retrieval_settings_panel.py` only drives widgets and session keys; load/save goes through **`BackendClient`** methods that call the same HTTP or in-process use cases (`get_effective_retrieval_settings` / `update_project_retrieval_settings`). Do not call the SQLite port from the panel.

## Preset semantics

No changes to `RetrievalPreset`, `PRESET_*` labels, or `from_preset` / `retrieval_settings_for_saved_project` behavior — tests in `tests/application/settings/test_retrieval_settings_use_cases.py` lock precise preset k/toggles and advanced merge, plus persistence round-trip.

## Angular / future clients

Treat `GET/PUT .../retrieval-settings` as the source of truth for project retrieval UX; optional overrides on ask/inspect endpoints remain separate from stored defaults.
