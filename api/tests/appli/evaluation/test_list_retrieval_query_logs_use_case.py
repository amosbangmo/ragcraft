from __future__ import annotations

from datetime import UTC, datetime
from application.dto.evaluation import ListRetrievalQueryLogsQuery
from application.use_cases.evaluation.list_retrieval_query_logs import ListRetrievalQueryLogsUseCase


def test_execute_passes_parsed_utc_bounds_to_port() -> None:
    captured: dict = {}

    class _Log:
        def load_logs(self, **kwargs):
            captured.update(kwargs)
            return []

    uc = ListRetrievalQueryLogsUseCase(query_log=_Log())
    uc.execute(
        ListRetrievalQueryLogsQuery(
            user_id="u",
            project_id="p",
            since_iso="2024-06-01T12:00:00Z",
            until_iso="2024-06-02T00:00:00+00:00",
            last_n=5,
        )
    )
    assert captured["last_n"] == 5
    assert isinstance(captured["since_utc"], datetime)
    assert captured["since_utc"].tzinfo == UTC
    assert isinstance(captured["until_utc"], datetime)


def test_execute_invalid_iso_becomes_none() -> None:
    captured: dict = {}

    class _Log:
        def load_logs(self, **kwargs):
            captured.update(kwargs)
            return []

    uc = ListRetrievalQueryLogsUseCase(query_log=_Log())
    uc.execute(
        ListRetrievalQueryLogsQuery(
            user_id="u",
            project_id="p",
            since_iso="not-a-date",
            until_iso="   ",
        )
    )
    assert captured["since_utc"] is None
    assert captured["until_utc"] is None


def test_execute_blank_since_until() -> None:
    captured: dict = {}

    class _Log:
        def load_logs(self, **kwargs):
            captured.update(kwargs)
            return []

    uc = ListRetrievalQueryLogsUseCase(query_log=_Log())
    uc.execute(ListRetrievalQueryLogsQuery(user_id="u", project_id="p", since_iso=None))
    assert captured["since_utc"] is None
