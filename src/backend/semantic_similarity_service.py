"""Deprecated compatibility alias; import from ``src.infrastructure.services.semantic_similarity_service`` instead."""
from importlib import import_module
import sys
_mod = import_module("src.infrastructure.services.semantic_similarity_service")
sys.modules[__name__] = _mod
