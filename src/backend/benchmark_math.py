"""Deprecated compatibility alias; import from ``src.domain.evaluation.benchmark_math`` instead."""
from importlib import import_module
import sys
_mod = import_module("src.domain.evaluation.benchmark_math")
sys.modules[__name__] = _mod
