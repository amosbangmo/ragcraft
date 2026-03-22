# RAG orchestration (final model)

## Entrypoints

| Entry | Mechanism |
|-------|-----------|
| **HTTP chat** | `apps/api/routers/chat.py` → `AskQuestionUseCase` via `apps/api/dependencies.py` |
| **In-process UI** | `src/frontend_gateway/in_process.py` → `container.chat_ask_question_use_case.execute(...)` |
| **Pipeline build only** | `BuildRagPipelineUseCase` (inspect/compare/eval paths) |
| **Inspect pipeline** | `InspectRagPipelineUseCase` (delegates to build use case) |
| **Preview summary recall** | `PreviewSummaryRecallUseCase` |
| **Answer from built pipeline** | `GenerateAnswerFromPipelineUseCase` |

Composition builds the graph in `src/composition/chat_rag_wiring.py` and exposes it through `BackendApplicationContainer.chat_rag_use_cases` and the `chat_*_use_case` properties.

## Main use cases (happy path ask)

1. **`AskQuestionUseCase`** — calls injected `build_pipeline` (bound to `BuildRagPipelineUseCase.execute`), then **`AnswerGenerationService`** for the LLM, optionally **`QueryLogPort`** after answer.
2. **`BuildRagPipelineUseCase`** — runs **`run_recall_then_assemble_pipeline`** then **`PipelineQueryLogEmitter.emit_after_pipeline_build`** when enabled.

## Orchestration sequence (application-owned)

**File:** `src/application/use_cases/chat/orchestration/recall_then_assemble_pipeline.py`

1. **`summary_recall_service.summary_recall_stage(...)`** — implements **`SummaryRecallStagePort`** (infrastructure: `SummaryRecallService`).
2. **`pipeline_assembly_service.build(...)`** — implements **`PipelineAssemblyPort`**. Implementation is **`ApplicationPipelineAssembly`** in application, which calls **`assemble_pipeline_from_recall`** (`assemble_pipeline_from_recall.py`).

**Post-recall assembly** (`assemble_pipeline_from_recall`): application code sequences:

- Docstore read → section expansion corpus policy (`section_expansion_corpus.py`) → **`SectionExpansionStagePort`** → **`AssetRerankingPort`** → compression → prompt sources → layout → multimodal hint → **`PromptRenderPort`** → **`RerankedConfidencePort`**.

**Technical implementations:** `src/infrastructure/adapters/rag/post_recall_stage_adapters.py` — one thin adapter class per port, delegating to existing services (`SectionRetrievalService`, `RerankingService`, `PromptBuilderService`, etc.).

## Ports involved (representative)

- **`SummaryRecallStagePort`**, **`PipelineAssemblyPort`** — recall + assembly boundary.
- **`PostRecallStagePorts`** (dataclass) — docstore read, section expansion, reranking, table QA hints, compression, prompt sources, layout, multimodal, prompt render, confidence.
- **`QueryLogPort`** — query logging (implemented by infrastructure query log service).
- Answer generation is not behind a domain port in all paths; **`AskQuestionUseCase`** takes **`AnswerGenerationService`** (concrete adapter) injected from composition.

## Where logging happens

- **After pipeline build (no answer yet):** `PipelineQueryLogEmitter` in `BuildRagPipelineUseCase.execute` when `emit_query_log=True`.
- **After full ask:** `AskQuestionUseCase` calls `query_log.log_query(...)` when configured, with merged latency including answer generation.

## Where answer generation happens

- **`src/infrastructure/adapters/rag/answer_generation_service.py`** — LLM invoke, used by **`AskQuestionUseCase`** and **`GenerateAnswerFromPipelineUseCase`**.

## Retrieval comparison

- **`CompareRetrievalModesUseCase`** — uses **`InspectRagPipelineUseCase`** (application); no direct RAG adapter imports from routers or gateway.

## Known sequencing still in infrastructure

- **`SummaryRecallService`** still contains substantial **retrieval-stage** sequencing (rewrite, hybrid recall, RRF, etc.) behind **`SummaryRecallStagePort`**. The **post-recall** assembly order is application-owned; recall **ordering** inside that service is an acceptable trade-off unless further split.
