# RAGCraft frontend (Streamlit)

- **Streamlit pages:** `frontend/pages/` (next to `app.py`).
- **Shared UI code:** `frontend/src/` (`components`, `services`, `utils`, …) — must stay on `PYTHONPATH`.

From the **repository root**, use **`scripts/run_streamlit.ps1`** (PowerShell) or **`scripts/run_streamlit.sh`** (Bash): they set `PYTHONPATH` to `api/src` + `frontend/src` and run `streamlit` from `frontend/`.

Manual equivalent from `frontend/`:

```bash
export PYTHONPATH="../api/src:../frontend/src"
python -m streamlit run app.py
```
