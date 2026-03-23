from __future__ import annotations

from application.common.pipeline_query_log import build_query_log_ingress_payload
from application.common.safe_query_log import log_query_safely
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.common.ports import QueryLogPort
from domain.projects.project import Project


class PipelineQueryLogEmitter:
    """
    Optional query-log write after a pipeline build.

    Implements :class:`~application.use_cases.chat.orchestration.ports.PipelineBuildQueryLogEmitterPort`.
    Keeps pipeline build use case free of inline logging branches; swallow errors via
    :func:`~application.common.safe_query_log.log_query_safely`.
    """

    __slots__ = ("_query_log",)

    def __init__(self, query_log: QueryLogPort | None) -> None:
        self._query_log = query_log

    def emit_after_pipeline_build(
        self,
        *,
        enabled: bool,
        project: Project,
        question: str,
        payload: PipelineBuildResult,
    ) -> None:
        if not enabled or self._query_log is None:
            return
        latency = payload.latency
        log_query_safely(
            self._query_log,
            build_query_log_ingress_payload(
                project=project,
                question=question,
                pipeline=payload,
                latency=latency,
            ),
        )
