# Architecture lock-in: lint + import-boundary tests. Run from repo root.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = if ($env:PYTHONPATH) { $env:PYTHONPATH } else { "." }
Write-Host "==> ruff check (src, apps, tests/architecture)"
ruff check src apps tests/architecture
Write-Host "==> pytest tests/architecture"
pytest tests/architecture -q --tb=short
