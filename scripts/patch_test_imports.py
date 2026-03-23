from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
repls = [
    ("from tests.apps_api.", "from apps_api."),
    ("from tests.architecture.", "from architecture."),
    ("from tests.support.", "from support."),
    ("from tests.fixtures.", "from fixtures."),
    ("from tests.quality.", "from e2e."),
]
for sub in ("api/tests", "frontend/tests"):
    base = ROOT / sub
    if not base.is_dir():
        continue
    for p in base.rglob("*.py"):
        t = p.read_text(encoding="utf-8")
        n = t
        for a, b in repls:
            n = n.replace(a, b)
        if n != t:
            p.write_text(n, encoding="utf-8")
            print("patched", p.relative_to(ROOT))
