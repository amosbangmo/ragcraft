class RAGCraftError(Exception):
    def __init__(self, message: str, user_message: str | None = None):
        super().__init__(message)
        self.user_message = user_message or message


class DocumentExtractionError(RAGCraftError):
    pass


class OCRDependencyError(DocumentExtractionError):
    pass


class LLMServiceError(RAGCraftError):
    pass


class VectorStoreError(RAGCraftError):
    pass


class DocStoreError(RAGCraftError):
    pass
