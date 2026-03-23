#!/usr/bin/env python3
"""Run from repository root: python scripts/run_structure_migration.py"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from migrate_phases import (
    phase_api_main,
    phase_application_reshape,
    phase_clear_partial,
    phase_composition_auth_wiring,
    phase_delete_old_roots,
    phase_frontend,
    phase_infrastructure_flatten,
    phase_move_core_to_api,
    phase_root_scripts,
    phase_split_domain,
    phase_tests,
)
from migrate_rewrite import apply_text_rewrites

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api"
API_SRC = API / "src"
FE = ROOT / "frontend"
FE_SRC = FE / "src"


def main() -> int:
    if not (ROOT / "src" / "domain").exists():
        print("Expected root src/domain — already migrated or wrong cwd?", file=sys.stderr)
        return 1
    phase_clear_partial(API, FE)
    phase_move_core_to_api(ROOT, API_SRC)
    phase_split_domain(API_SRC)
    phase_application_reshape(API_SRC)
    phase_infrastructure_flatten(API_SRC)
    phase_composition_auth_wiring(API_SRC)
    phase_frontend(ROOT, FE, FE_SRC, API_SRC)
    phase_tests(ROOT, API, FE)
    phase_api_main(API)
    phase_delete_old_roots(ROOT)
    phase_root_scripts(ROOT)
    apply_text_rewrites(ROOT, API, FE)
    print("Migration finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
