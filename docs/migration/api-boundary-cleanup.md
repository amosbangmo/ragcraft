# HTTP API boundary cleanup (framework leaks)

## What was removed from `apps/api`

- **LangChain `Document` imports** in `apps/api/schemas/serialization.py`. The API package no longer branches on framework types when building JSON.
- **Duplicated normalization logic** now lives in a single place: `src/infrastructure/web/json_normalization.py` (`jsonify_value`), invoked through thin helpers in `apps/api/schemas/serialization.py`.

## Backward compatibility

- **Unchanged wire shapes:** chat answers still expose `source_documents` / preview / pipeline snippets as `{"page_content": str, "metadata": dict}` where documents appear — the same JSON clients already received.
- **Benchmark run:** `POST /evaluation/dataset/run` now runs the same normalizer over `BenchmarkResult.to_dict()` so deeply nested row `data` cannot leak non-JSON types; keys and semantics are intended to match the previous `model_validate(result.to_dict())` path for plain dict/JSON-native content.

## Explicit contracts

- `apps/api/schemas/plain_payloads.py` adds **TypedDict** descriptions for common payload fragments (source documents, raw assets, preview, RAG answer). They document intent; responses may include additional keys where Pydantic `extra` policy allows.

## What remains to clean later

- **Domain models** still reference `langchain_core.documents.Document` (e.g. `PipelineBuildResult`, ports). A future step is a domain-neutral document DTO and adapters in infrastructure only.
- **Pydantic models** under `apps/api/schemas/*` still use `list[dict[str, Any]]` for flexible subtrees; stricter nested models could be introduced behind a **v2** API if you ever need to tighten the contract.
- **Manual evaluation** and other routes that call `.to_dict()` on domain objects should be audited the same way as benchmarks if any path starts embedding framework objects inside those dicts.
- **`apps/api/dependencies.py`** comments still mention deferring FAISS/LangChain loads — that is about import-time cost, not type leakage.
