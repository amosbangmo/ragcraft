"""Deprecated compatibility alias; import from ``src.infrastructure.services.qa_dataset_service`` instead."""
from importlib import import_module
import sys
_mod = import_module("src.infrastructure.services.qa_dataset_service")
sys.modules[__name__] = _mod
