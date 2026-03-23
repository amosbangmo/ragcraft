# Infrastructure service tests

Unit tests for **`infrastructure.adapters`** (RAG orchestration, docstore, vector store, evaluation, ingestion, etc.).

This tree lives under **`api/tests/infra/`** (short name; avoids clashing with the production **`infrastructure`** package on **`PYTHONPATH`**).

Run with pytest (full suite via **`scripts/run_tests.sh`**) or unittest from the repo root:

```bash
python -m unittest discover -s api/tests/infra -p "test_*.py"
```
