"""
FastAPI dependency providers (transport layer).

**Composition root:** :func:`get_backend_application_container` returns a cached
:class:`~src.composition.application_container.BackendApplicationContainer` built via
:func:`~src.composition.build_backend` with :func:`~src.composition.wiring.process_scoped_chain_invalidate_key`.
The service-level graph (:class:`~src.composition.backend_composition.BackendComposition`) contains
technical adapters only; it is built via :func:`~src.composition.build_backend_composition`.

FastAPI does not reference ``src.app`` or the legacy interactive UI shell.

Importing this module loads the composition package (typed service + use-case graph) so dependency
signatures stay explicit; the container **instance** is still created lazily on first
:func:`get_backend_application_container` call (``lru_cache``).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from src.application.use_cases.chat.ask_question import AskQuestionUseCase
from src.application.use_cases.retrieval.compare_retrieval_modes import CompareRetrievalModesUseCase
from src.application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
from src.application.use_cases.chat.preview_summary_recall import PreviewSummaryRecallUseCase
from src.application.use_cases.evaluation.build_benchmark_export_artifacts import (
    BuildBenchmarkExportArtifactsUseCase,
)
from src.application.use_cases.evaluation.create_qa_dataset_entry import CreateQaDatasetEntryUseCase
from src.application.use_cases.evaluation.delete_qa_dataset_entry import DeleteQaDatasetEntryUseCase
from src.application.use_cases.evaluation.generate_qa_dataset import GenerateQaDatasetUseCase
from src.application.use_cases.evaluation.list_qa_dataset_entries import ListQaDatasetEntriesUseCase
from src.application.use_cases.evaluation.list_retrieval_query_logs import ListRetrievalQueryLogsUseCase
from src.application.use_cases.evaluation.run_gold_qa_dataset_evaluation import (
    RunGoldQaDatasetEvaluationUseCase,
)
from src.application.use_cases.evaluation.run_manual_evaluation import RunManualEvaluationUseCase
from src.application.use_cases.evaluation.update_qa_dataset_entry import UpdateQaDatasetEntryUseCase
from src.application.use_cases.ingestion.delete_document import DeleteDocumentUseCase
from src.application.use_cases.ingestion.ingest_uploaded_file import IngestUploadedFileUseCase
from src.application.use_cases.ingestion.reindex_document import ReindexDocumentUseCase
from src.application.use_cases.projects.create_project import CreateProjectUseCase
from src.application.use_cases.projects.get_project_document_details import GetProjectDocumentDetailsUseCase
from src.application.use_cases.projects.get_project_retrieval_preset_label import (
    GetProjectRetrievalPresetLabelUseCase,
)
from src.application.use_cases.projects.invalidate_project_chain_cache import (
    InvalidateProjectChainCacheUseCase,
)
from src.application.use_cases.projects.list_document_assets_for_source import (
    ListDocumentAssetsForSourceUseCase,
)
from src.application.use_cases.projects.list_project_documents import ListProjectDocumentsUseCase
from src.application.use_cases.projects.list_projects import ListProjectsUseCase
from src.application.use_cases.projects.resolve_project import ResolveProjectUseCase
from src.application.use_cases.settings.get_effective_retrieval_settings import (
    GetEffectiveRetrievalSettingsUseCase,
)
from src.application.use_cases.settings.update_project_retrieval_settings import (
    UpdateProjectRetrievalSettingsUseCase,
)
from src.application.auth.authenticated_principal import AuthenticatedPrincipal
from src.application.use_cases.auth.login_user import LoginUserUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.application.use_cases.users.change_user_password import ChangeUserPasswordUseCase
from src.application.use_cases.users.delete_user_account import DeleteUserAccountUseCase
from src.application.use_cases.users.get_current_user_profile import GetCurrentUserProfileUseCase
from src.application.use_cases.users.remove_user_avatar import RemoveUserAvatarUseCase
from src.application.use_cases.users.update_user_profile import UpdateUserProfileUseCase
from src.application.use_cases.users.upload_user_avatar import UploadUserAvatarUseCase
from src.domain.ports.user_repository_port import UserRepositoryPort
from src.composition.application_container import BackendApplicationContainer


@lru_cache(maxsize=1)
def get_backend_application_container() -> BackendApplicationContainer:
    from src.application.frontend_support.memory_chat_transcript import MemoryChatTranscript
    from src.composition import build_backend, build_backend_composition
    from src.composition.wiring import process_scoped_chain_invalidate_key

    return build_backend(
        invalidate_chain_key=process_scoped_chain_invalidate_key(),
        backend=build_backend_composition(chat_transcript=MemoryChatTranscript()),
    )


BackendContainerDep = Annotated[BackendApplicationContainer, Depends(get_backend_application_container)]


def _raw_x_user_id_header(
    x_user_id: Annotated[
        str | None,
        Header(
            alias="X-User-Id",
            description=(
                "Required workspace user id. Extension point: resolve a verified "
                ":class:`~src.application.auth.authenticated_principal.AuthenticatedPrincipal` "
                "from OAuth/JWT without changing route paths."
            ),
        ),
    ] = None,
) -> str:
    if x_user_id is None or not str(x_user_id).strip():
        raise HTTPException(
            status_code=400,
            detail="Missing or empty X-User-Id header.",
        )
    return str(x_user_id).strip()


def get_authenticated_principal(raw_user_id: Annotated[str, Depends(_raw_x_user_id_header)]) -> AuthenticatedPrincipal:
    """Trusted application identity for routes that require ``X-User-Id``."""
    return AuthenticatedPrincipal(user_id=raw_user_id.strip(), auth_method="x_user_id_header", is_authenticated=True)


def get_list_projects_use_case(container: BackendContainerDep) -> ListProjectsUseCase:
    return container.projects_list_projects_use_case


def get_create_project_use_case(container: BackendContainerDep) -> CreateProjectUseCase:
    return container.projects_create_project_use_case


def get_get_effective_retrieval_settings_use_case(
    container: BackendContainerDep,
) -> GetEffectiveRetrievalSettingsUseCase:
    return container.settings_get_effective_retrieval_use_case


def get_update_project_retrieval_settings_use_case(
    container: BackendContainerDep,
) -> UpdateProjectRetrievalSettingsUseCase:
    return container.settings_update_project_retrieval_use_case


def get_list_project_documents_use_case(container: BackendContainerDep) -> ListProjectDocumentsUseCase:
    return container.projects_list_project_documents_use_case


def get_resolve_project_use_case(container: BackendContainerDep) -> ResolveProjectUseCase:
    return container.projects_resolve_project_use_case


def get_get_project_document_details_use_case(
    container: BackendContainerDep,
) -> GetProjectDocumentDetailsUseCase:
    return container.projects_get_project_document_details_use_case


def get_list_document_assets_for_source_use_case(
    container: BackendContainerDep,
) -> ListDocumentAssetsForSourceUseCase:
    return container.projects_list_document_assets_for_source_use_case


def get_get_project_retrieval_preset_label_use_case(
    container: BackendContainerDep,
) -> GetProjectRetrievalPresetLabelUseCase:
    return container.projects_get_retrieval_preset_label_use_case


def get_invalidate_project_chain_cache_use_case(
    container: BackendContainerDep,
) -> InvalidateProjectChainCacheUseCase:
    return container.projects_invalidate_project_chain_cache_use_case


def get_compare_retrieval_modes_use_case(
    container: BackendContainerDep,
) -> CompareRetrievalModesUseCase:
    return container.chat_compare_retrieval_modes_use_case


def get_ask_question_use_case(container: BackendContainerDep) -> AskQuestionUseCase:
    return container.chat_ask_question_use_case


def get_inspect_pipeline_use_case(container: BackendContainerDep) -> InspectRagPipelineUseCase:
    return container.chat_inspect_pipeline_use_case


def get_preview_summary_recall_use_case(container: BackendContainerDep) -> PreviewSummaryRecallUseCase:
    return container.chat_preview_summary_recall_use_case


def get_create_qa_dataset_entry_use_case(container: BackendContainerDep) -> CreateQaDatasetEntryUseCase:
    return container.evaluation_create_qa_dataset_entry_use_case


def get_list_qa_dataset_entries_use_case(container: BackendContainerDep) -> ListQaDatasetEntriesUseCase:
    return container.evaluation_list_qa_dataset_entries_use_case


def get_build_benchmark_export_artifacts_use_case(
    container: BackendContainerDep,
) -> BuildBenchmarkExportArtifactsUseCase:
    return container.evaluation_build_benchmark_export_artifacts_use_case


def get_run_manual_evaluation_use_case(container: BackendContainerDep) -> RunManualEvaluationUseCase:
    return container.evaluation_run_manual_evaluation_use_case


def get_run_gold_qa_dataset_evaluation_use_case(
    container: BackendContainerDep,
) -> RunGoldQaDatasetEvaluationUseCase:
    return container.evaluation_run_gold_qa_dataset_evaluation_use_case


def get_update_qa_dataset_entry_use_case(container: BackendContainerDep) -> UpdateQaDatasetEntryUseCase:
    return container.evaluation_update_qa_dataset_entry_use_case


def get_delete_qa_dataset_entry_use_case(container: BackendContainerDep) -> DeleteQaDatasetEntryUseCase:
    return container.evaluation_delete_qa_dataset_entry_use_case


def get_generate_qa_dataset_use_case(container: BackendContainerDep) -> GenerateQaDatasetUseCase:
    return container.evaluation_generate_qa_dataset_use_case


def get_list_retrieval_query_logs_use_case(
    container: BackendContainerDep,
) -> ListRetrievalQueryLogsUseCase:
    return container.evaluation_list_retrieval_query_logs_use_case


def get_ingest_uploaded_file_use_case(container: BackendContainerDep) -> IngestUploadedFileUseCase:
    return container.ingestion_ingest_uploaded_file_use_case


def get_reindex_document_use_case(container: BackendContainerDep) -> ReindexDocumentUseCase:
    return container.ingestion_reindex_document_use_case


def get_delete_document_use_case(container: BackendContainerDep) -> DeleteDocumentUseCase:
    return container.ingestion_delete_document_use_case


def get_user_repository(container: BackendContainerDep) -> UserRepositoryPort:
    """
    User persistence for auth and profile routes (same instance as
    :class:`~src.auth.auth_service.AuthService` on the default graph).

    Resolved from the composition root so FastAPI does not import concrete SQLite adapters.
    """
    return container.backend.auth_service.user_repository


UserRepositoryDep = Annotated[UserRepositoryPort, Depends(get_user_repository)]


def get_login_user_use_case(
    repo: UserRepositoryDep,
    container: BackendContainerDep,
) -> LoginUserUseCase:
    return LoginUserUseCase(users=repo, password_hasher=container.backend.password_hasher)


def get_register_user_use_case(
    repo: UserRepositoryDep,
    container: BackendContainerDep,
) -> RegisterUserUseCase:
    return RegisterUserUseCase(users=repo, password_hasher=container.backend.password_hasher)


def get_get_current_user_profile_use_case(repo: UserRepositoryDep) -> GetCurrentUserProfileUseCase:
    return GetCurrentUserProfileUseCase(users=repo)


def get_update_user_profile_use_case(repo: UserRepositoryDep) -> UpdateUserProfileUseCase:
    return UpdateUserProfileUseCase(users=repo)


def get_change_user_password_use_case(
    repo: UserRepositoryDep,
    container: BackendContainerDep,
) -> ChangeUserPasswordUseCase:
    return ChangeUserPasswordUseCase(users=repo, password_hasher=container.backend.password_hasher)


def get_upload_user_avatar_use_case(
    repo: UserRepositoryDep,
    container: BackendContainerDep,
) -> UploadUserAvatarUseCase:
    return UploadUserAvatarUseCase(users=repo, avatar_storage=container.backend.avatar_storage)


def get_remove_user_avatar_use_case(
    repo: UserRepositoryDep,
    container: BackendContainerDep,
) -> RemoveUserAvatarUseCase:
    return RemoveUserAvatarUseCase(users=repo, avatar_storage=container.backend.avatar_storage)


def get_delete_user_account_use_case(
    repo: UserRepositoryDep,
    container: BackendContainerDep,
) -> DeleteUserAccountUseCase:
    return DeleteUserAccountUseCase(
        users=repo,
        password_hasher=container.backend.password_hasher,
        avatar_storage=container.backend.avatar_storage,
    )
