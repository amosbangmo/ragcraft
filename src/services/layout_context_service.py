"""
Layout-aware grouping of retrieved assets (service façade over domain rules).

Domain implementation: :mod:`src.domain.retrieval.layout_grouping`.
"""

from __future__ import annotations

from src.domain.retrieval.layout_grouping import (
    describe_layout_group,
    group_assets_by_layout,
    validate_layout_groups,
)

__all__ = [
    "LayoutContextService",
    "describe_layout_group",
]


class LayoutContextService:
    """
    Groups assets that share layout signals (file, page, section) and are element-nearby,
    preserving global rerank order within each group.
    """

    def group_assets(self, assets: list[dict]) -> list[list[dict]]:
        return group_assets_by_layout(assets)

    def validate_groups(self, assets: list[dict], groups: list[list[dict]]) -> bool:
        return validate_layout_groups(assets, groups)
