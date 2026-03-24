# RAGCraft frontend (Streamlit)

- **Streamlit pages:** `frontend/pages/` (next to `app.py`).
- **Shared UI code:** `frontend/src/` (`components`, `services`, `utils`, …) — must stay on `PYTHONPATH`.

Run from `frontend/`: `streamlit run app.py` with `PYTHONPATH` including `frontend/src` (see repo `pyproject.toml`).
