# Ruff on api/src, frontend/src, frontend/pages, and architecture tests.
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArguments = @()
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Ruff check (api/src, frontend/src, frontend/pages, api/tests/architecture)"
& python -m ruff check "$Root/api/src" "$Root/frontend/src" "$Root/frontend/pages" "$Root/api/tests/architecture" @RemainingArguments
