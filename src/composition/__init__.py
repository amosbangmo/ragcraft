"""Composition roots for assembling the backend without a DI framework."""

from src.composition.backend_composition import BackendComposition, build_backend_composition

__all__ = [
    "BackendComposition",
    "build_backend_composition",
]
