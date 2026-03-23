# Infrastructure service tests

Unit tests for **`infrastructure.adapters`** (RAG orchestration, docstore, vector store, evaluation, ingestion, etc.).

This package was renamed from **`tests/backend`** so it is not confused with the **HTTP API** (`apps/api/`). The legacy **`src/backend/`** Python package has been removed from the tree.

Run with pytest (entire suite) or unittest:

```bash
python -m unittest discover -s tests/infrastructure_services -p "test_*.py"
```
