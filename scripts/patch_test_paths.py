from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
repls = [
    ('REPO_ROOT / "src" /', 'REPO_ROOT / "api" / "src" /'),
    ('REPO_ROOT / "apps" / "api" /', 'REPO_ROOT / "api" / "src" / "interfaces" / "http" /'),
    ('REPO_ROOT / "pages"', 'REPO_ROOT / "frontend" / "src" / "pages"'),
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
