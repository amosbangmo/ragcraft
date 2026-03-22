"""Deprecated compatibility alias; import from ``src.infrastructure.services.query_log_service`` instead."""
from importlib import import_module
import sys
_mod = import_module("src.infrastructure.services.query_log_service")
sys.modules[__name__] = _mod
