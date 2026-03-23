# Architecture lock-in: lint + import-boundary tests. Run from repo root.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = "$Root/api/src;$Root/frontend/src;$Root/api/tests"
Write-Host "==> ruff check (api/src, frontend/src, api/tests/architecture)"
ruff check api/src frontend/src api/tests/architecture
Write-Host "==> pytest api/tests/architecture"
pytest api/tests/architecture -q --tb=short
