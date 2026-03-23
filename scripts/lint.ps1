# Ruff on api/src, frontend/src, and architecture tests.
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArguments = @()
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Ruff check (api/src, frontend/src, api/tests/architecture)"
& python -m ruff check "$Root/api/src" "$Root/frontend/src" "$Root/api/tests/architecture" @RemainingArguments
