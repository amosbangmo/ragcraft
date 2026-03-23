from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LanguageModelGateway(Protocol):
    """
    Minimal chat-model invocation surface used by RAG answer paths.

    Implementations typically wrap a LangChain runnable; callers read ``content``
    from the returned object when present.
    """

    def invoke(self, prompt: str) -> Any: ...
