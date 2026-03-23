# Blocking architecture tests only. Run from repo root (PowerShell).
# Equivalent to scripts/validate_architecture.sh
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArguments = @()
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = "$Root/api/src;$Root/frontend/src;$Root/api/tests"

Write-Host "==> Architecture + bootstrap runtime checks (api/tests/architecture, api/tests/bootstrap)"
& python -m pytest api/tests/architecture api/tests/bootstrap -q @RemainingArguments
