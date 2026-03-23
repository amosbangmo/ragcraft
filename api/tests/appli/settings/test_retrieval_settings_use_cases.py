"""Application-layer retrieval settings: preset merge and persistence (in-memory port)."""

from __future__ import annotations

from application.dto.settings import (
    GetEffectiveRetrievalSettingsQuery,
    UpdateProjectRetrievalSettingsCommand,
)
from application.services.retrieval_settings_tuner import RetrievalSettingsTuner
from application.use_cases.settings.get_effective_retrieval_settings import (
    GetEffectiveRetrievalSettingsUseCase,
)
from application.use_cases.settings.update_project_retrieval_settings import (
    UpdateProjectRetrievalSettingsUseCase,
)
from domain.projects.project_settings import ProjectSettings, default_project_settings
from domain.rag.retrieval_presets import PRESET_UI_LABELS, RetrievalPreset


class _MemoryProjectSettingsRepo:
    """Minimal port backing store for tests (no SQLite)."""

    def __init__(self) -> None:
        self._rows: dict[tuple[str, str], ProjectSettings] = {}

    def load(self, user_id: str, project_id: str) -> ProjectSettings:
        key = (user_id, project_id)
        if key not in self._rows:
            return default_project_settings(user_id, project_id)
        return self._rows[key]

    def save(self, settings: ProjectSettings) -> None:
        self._rows[(settings.user_id, settings.project_id)] = settings


def test_get_effective_precise_preset_semantics_match_service() -> None:
    repo = _MemoryProjectSettingsRepo()
    retrieval = RetrievalSettingsTuner(project_settings_repository=repo)
    repo._rows[("u", "p")] = ProjectSettings(
        user_id="u",
        project_id="p",
        retrieval_preset=RetrievalPreset.PRECISE.value,
        retrieval_advanced=False,
        enable_query_rewrite=True,
        enable_hybrid_retrieval=False,
    )
    uc = GetEffectiveRetrievalSettingsUseCase(
        project_settings=repo,
        retrieval_settings=retrieval,
    )
    view = uc.execute(GetEffectiveRetrievalSettingsQuery(user_id="u", project_id="p"))
    assert view.preferences.retrieval_preset == RetrievalPreset.PRECISE.value
    direct = retrieval.from_preset(RetrievalPreset.PRECISE.value)
    assert view.effective_retrieval.enable_query_rewrite == direct.enable_query_rewrite
    assert view.effective_retrieval.enable_hybrid_retrieval == direct.enable_hybrid_retrieval
    assert view.effective_retrieval.similarity_search_k == direct.similarity_search_k


def test_get_effective_advanced_overrides_merge() -> None:
    repo = _MemoryProjectSettingsRepo()
    retrieval = RetrievalSettingsTuner(project_settings_repository=repo)
    repo._rows[("u", "p")] = ProjectSettings(
        user_id="u",
        project_id="p",
        retrieval_preset=RetrievalPreset.PRECISE.value,
        retrieval_advanced=True,
        enable_query_rewrite=False,
        enable_hybrid_retrieval=True,
    )
    uc = GetEffectiveRetrievalSettingsUseCase(project_settings=repo, retrieval_settings=retrieval)
    view = uc.execute(GetEffectiveRetrievalSettingsQuery(user_id="u", project_id="p"))
    assert view.effective_retrieval.enable_query_rewrite is False
    assert view.effective_retrieval.enable_hybrid_retrieval is True
    assert (
        view.effective_retrieval.similarity_search_k
        == retrieval.from_preset(RetrievalPreset.PRECISE.value).similarity_search_k
    )


def test_update_accepts_legacy_ui_preset_label() -> None:
    """Router/UI may still send title-case labels; preset parser normalizes to canonical values."""
    repo = _MemoryProjectSettingsRepo()
    update_uc = UpdateProjectRetrievalSettingsUseCase(project_settings=repo)
    exploratory_label = PRESET_UI_LABELS[RetrievalPreset.EXPLORATORY]
    out = update_uc.execute(
        UpdateProjectRetrievalSettingsCommand(
            user_id="alice",
            project_id="demo",
            retrieval_preset=exploratory_label,
            retrieval_advanced=False,
            enable_query_rewrite=True,
            enable_hybrid_retrieval=True,
        )
    )
    assert out.retrieval_preset == RetrievalPreset.EXPLORATORY.value


def test_update_then_load_round_trip() -> None:
    repo = _MemoryProjectSettingsRepo()
    update_uc = UpdateProjectRetrievalSettingsUseCase(project_settings=repo)
    out = update_uc.execute(
        UpdateProjectRetrievalSettingsCommand(
            user_id="alice",
            project_id="demo",
            retrieval_preset="exploratory",
            retrieval_advanced=True,
            enable_query_rewrite=False,
            enable_hybrid_retrieval=True,
        )
    )
    assert out.retrieval_preset == RetrievalPreset.EXPLORATORY.value
    loaded = repo.load("alice", "demo")
    assert loaded.retrieval_advanced is True
    assert loaded.enable_query_rewrite is False
    assert loaded.enable_hybrid_retrieval is True
    assert loaded.retrieval_preset == RetrievalPreset.EXPLORATORY.value
