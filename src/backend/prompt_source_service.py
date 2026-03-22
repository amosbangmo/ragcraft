"""Deprecated compatibility alias; import from ``src.infrastructure.services.prompt_source_service`` instead."""
from importlib import import_module
import sys
_mod = import_module("src.infrastructure.services.prompt_source_service")
sys.modules[__name__] = _mod
