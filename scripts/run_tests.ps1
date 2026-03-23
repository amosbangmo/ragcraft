# Full pytest workflow: architecture first, then remaining api + frontend tests.
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArguments = @()
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = "$Root/api/src;$Root/frontend/src;$Root/api/tests"

Write-Host "==> Step 1/2: Architecture guardrails (blocking)"
& "$PSScriptRoot\validate_architecture.ps1"

$apiTests = Join-Path $Root "api/tests"
$archTests = Join-Path $Root "api/tests/architecture"
$frontendTests = Join-Path $Root "frontend/tests"

Write-Host "==> Step 2/2: Pytest (api/tests minus architecture + frontend/tests)"
& python -m pytest $apiTests --ignore=$archTests $frontendTests -q @RemainingArguments
