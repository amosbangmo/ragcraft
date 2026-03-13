from dataclasses import dataclass
from typing import Any


@dataclass
class SourceCitation:
    source_number: int
    doc_id: str
    source_file: str
    content_type: str
    page_label: str | None
    locator_label: str | None
    display_label: str
    prompt_label: str
    metadata: dict[str, Any]
