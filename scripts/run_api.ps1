# FastAPI via uvicorn: PYTHONPATH is the repository root (so api.main resolves).
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArguments = @()
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = $Root
Write-Host "==> uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 (cwd=$Root)"
& python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 @RemainingArguments
