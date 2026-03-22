"""Re-exports retrieval preset merge port (canonical definition lives in ``src.domain.ports``)."""

from __future__ import annotations

from src.application.settings.retrieval_merge_default import default_retrieval_preset_merge_port
from src.domain.ports.retrieval_preset_merge_port import RetrievalPresetMergePort

__all__ = ["RetrievalPresetMergePort", "default_retrieval_preset_merge_port"]
