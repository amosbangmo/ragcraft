# Streamlit UI: sets PYTHONPATH for frontend/src + api/src, runs from frontend/.
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArguments = @()
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"
Set-Location $Frontend
$env:PYTHONPATH = "$Root/api/src;$Root/frontend/src"
Write-Host "==> python -m streamlit run app.py (cwd=$Frontend)"
& python -m streamlit run app.py @RemainingArguments
