"""Deprecated compatibility alias; import from ``src.infrastructure.services.benchmark_comparison_service`` instead."""
from importlib import import_module
import sys
_mod = import_module("src.infrastructure.services.benchmark_comparison_service")
sys.modules[__name__] = _mod
