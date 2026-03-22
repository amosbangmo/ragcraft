"""
Shared RAG pipeline orchestration helpers (no transport or UI).

Avoid importing :mod:`recall_then_assemble_pipeline` here so ``from … import PipelineQueryLogEmitter``
does not pull FAISS / LangChain in minimal test environments.
"""

from src.application.chat.orchestration.pipeline_query_log_emitter import PipelineQueryLogEmitter

__all__ = ["PipelineQueryLogEmitter"]
