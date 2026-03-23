# Quick CI-style lock-in: lint + blocking architecture tests.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& "$PSScriptRoot\lint.ps1"
& "$PSScriptRoot\validate_architecture.ps1" --tb=short
