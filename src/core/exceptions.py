"""
RAGCraft exception taxonomy.

Layers (``layer``) classify errors for logging, metrics, and HTTP mapping:

- **domain** — model invariants and semantic rules (invalid IDs, illegal transitions).
- **application** — use-case orchestration and app-level validation.
- **infrastructure** — I/O, external services, vector store, SQLite, LLM APIs, parsers.

Subclasses set ``default_status`` (HTTP) and ``error_code`` (stable API identifier).
``str(exception)`` is the **internal** message (logs, debugging); ``user_message`` is safe
for clients when it differs from technical detail.
"""

from __future__ import annotations

from typing import ClassVar


class RAGCraftError(Exception):
    """
    Root type for all handled RAGCraft errors.

    Parameters
    ----------
    message
        Internal / technical description. Available as ``str(exc)`` for logs.
    user_message
        Human-readable text suitable for UI and HTTP responses. Defaults to ``message``.
    code
        Optional override for the stable ``error_code`` (normally taken from the class).
    """

    default_status: ClassVar[int] = 500
    error_code: ClassVar[str] = "internal_error"
    layer: ClassVar[str] = "unknown"

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        *,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.user_message = user_message or message
        self._code_override = code

    @property
    def internal_message(self) -> str:
        """Technical message for logs (same as ``str(self)``)."""
        if self.args:
            return str(self.args[0])
        return str(self)

    @property
    def resolved_error_code(self) -> str:
        return self._code_override or type(self).error_code

    def http_status(self) -> int:
        """Preferred HTTP status for this exception instance."""
        return type(self).default_status


class DomainError(RAGCraftError):
    """Domain model invariant or semantic violation."""

    default_status = 400
    error_code = "domain_error"
    layer = "domain"


class ApplicationError(RAGCraftError):
    """Use-case rule, coordination failure, or application-level validation."""

    default_status = 400
    error_code = "application_error"
    layer = "application"


class InfrastructureError(RAGCraftError):
    """External system, storage, network, or environment failure."""

    default_status = 503
    error_code = "infrastructure_error"
    layer = "infrastructure"


# --- Infrastructure: ingestion & multimodal ---


class DocumentExtractionError(InfrastructureError):
    """Could not extract structured content from a document."""

    default_status = 503
    error_code = "document_extraction_failed"


class OCRDependencyError(DocumentExtractionError):
    """OCR stack (e.g. Tesseract) missing or misconfigured."""

    error_code = "ocr_dependency_error"


# --- Infrastructure: model & stores ---


class LLMServiceError(InfrastructureError):
    """Upstream LLM or judge call failed."""

    default_status = 502
    error_code = "llm_service_failed"


class VectorStoreError(InfrastructureError):
    """Vector index (e.g. FAISS) operation failed."""

    error_code = "vector_store_unavailable"


class DocStoreError(InfrastructureError):
    """Document / asset persistence (e.g. SQLite) failed."""

    error_code = "doc_store_unavailable"
