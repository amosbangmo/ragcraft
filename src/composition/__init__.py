"""Composition roots for assembling the backend without a DI framework."""

from src.composition.application_container import (
    BackendApplicationContainer,
    build_backend_application_container,
)
from src.composition.backend_composition import BackendComposition, build_backend_composition

__all__ = [
    "BackendApplicationContainer",
    "BackendComposition",
    "build_backend_application_container",
    "build_backend_composition",
]
