from dataclasses import dataclass
from typing import Any


@dataclass
class RetrievedAsset:
    doc_id: str
    project_id: str
    user_id: str
    source_file: str
    content_type: str  # text | table | image
    raw_content: str
    summary: str
    metadata: dict[str, Any]
