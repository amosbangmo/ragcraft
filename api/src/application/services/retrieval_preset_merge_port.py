"""Re-exports retrieval preset merge port (canonical definition lives in ``domain.ports``)."""

from __future__ import annotations

from application.services.retrieval_merge_default import default_retrieval_preset_merge_port
from domain.common.ports.retrieval_preset_merge_port import RetrievalPresetMergePort

__all__ = ["RetrievalPresetMergePort", "default_retrieval_preset_merge_port"]
