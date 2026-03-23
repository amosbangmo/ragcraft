from __future__ import annotations

import pytest

from src.domain.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec


def test_from_optional_mapping_none_and_empty() -> None:
    assert RetrievalSettingsOverrideSpec.from_optional_mapping(None) is None
    assert RetrievalSettingsOverrideSpec.from_optional_mapping({}) is None


def test_from_optional_mapping_rejects_unknown_keys() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        RetrievalSettingsOverrideSpec.from_optional_mapping({"not_a_field": 1})


def test_as_merge_mapping_round_trip() -> None:
    spec = RetrievalSettingsOverrideSpec.from_optional_mapping({"similarity_search_k": 7})
    assert spec is not None
    assert spec.as_merge_mapping() == {"similarity_search_k": 7}
