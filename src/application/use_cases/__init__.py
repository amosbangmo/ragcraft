"""
Explicit application use-case packages (Clean Architecture orchestration).

- ``projects`` — workspace and document listing
- ``ingestion`` — upload, reindex, delete
- ``chat`` — RAG pipeline, ask, inspect, summary preview
- ``retrieval`` — retrieval-mode comparison and related flows
- ``evaluation`` — benchmarks, QA dataset, exports, query logs
- ``settings`` — effective retrieval settings for a project

Import concrete types from submodules, e.g.
``from src.application.use_cases.chat.ask_question import AskQuestionUseCase``.
"""
