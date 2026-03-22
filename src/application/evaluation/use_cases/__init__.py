"""Evaluation use cases.

Lazy exports avoid pulling every evaluation submodule when the package is initialized (e.g. as a
parent of ``run_manual_evaluation``).
"""

from __future__ import annotations

import importlib
from typing import Any

from src.application.evaluation.dtos import GenerateQaDatasetCommand

__all__ = [
    "BenchmarkExecutionUseCase",
    "BuildBenchmarkExportArtifactsUseCase",
    "CreateQaDatasetEntryUseCase",
    "DeleteAllQaDatasetEntriesUseCase",
    "DeleteQaDatasetEntryUseCase",
    "GenerateQaDatasetCommand",
    "GenerateQaDatasetUseCase",
    "ListQaDatasetEntriesUseCase",
    "UpdateQaDatasetEntryUseCase",
]

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "BenchmarkExecutionUseCase": ("benchmark_execution", "BenchmarkExecutionUseCase"),
    "BuildBenchmarkExportArtifactsUseCase": (
        "build_benchmark_export_artifacts",
        "BuildBenchmarkExportArtifactsUseCase",
    ),
    "CreateQaDatasetEntryUseCase": ("create_qa_dataset_entry", "CreateQaDatasetEntryUseCase"),
    "DeleteAllQaDatasetEntriesUseCase": (
        "delete_all_qa_dataset_entries",
        "DeleteAllQaDatasetEntriesUseCase",
    ),
    "DeleteQaDatasetEntryUseCase": ("delete_qa_dataset_entry", "DeleteQaDatasetEntryUseCase"),
    "GenerateQaDatasetUseCase": ("generate_qa_dataset", "GenerateQaDatasetUseCase"),
    "ListQaDatasetEntriesUseCase": ("list_qa_dataset_entries", "ListQaDatasetEntriesUseCase"),
    "UpdateQaDatasetEntryUseCase": ("update_qa_dataset_entry", "UpdateQaDatasetEntryUseCase"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_ATTRS:
        mod_name, attr = _LAZY_ATTRS[name]
        mod = importlib.import_module(f"{__name__}.{mod_name}")
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
