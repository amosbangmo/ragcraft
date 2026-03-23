# Generate artifacts/ (coverage, junit, benchmark text, CI-equivalent log).
# Run from anywhere; switches to repo root automatically.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
& python "$PSScriptRoot\generate_artifacts.py" @args
