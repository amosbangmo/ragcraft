
import uuid
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def create_chunks(
    text: str,
    project_id: str,
    file_name: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> List[Document]:
    """
    Split documents into chunks and enrich them with metadata
    for RAG retrieval and traceability.
    """

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    document_id = str(uuid.uuid4())

    # split_docs = text_splitter.split_documents(documents)

    split_docs = text_splitter.create_documents(
        [text],
        metadatas=[{"source": file_name}]
    )
    
    chunks = []

    for i, doc in enumerate(split_docs):

        metadata = {
            "project_id": project_id,
            "document_id": document_id,
            "file_name": file_name,
            "chunk_id": i,
            "chunk_size": len(doc.page_content)
        }

        chunk = Document(
            page_content=doc.page_content,
            metadata=metadata
        )

        chunks.append(chunk)

    return chunks