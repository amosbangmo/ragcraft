$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvActivate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"

if (Test-Path $venvActivate) {
    . $venvActivate
} else {
    Write-Warning "Virtual environment activation script not found at $venvActivate. Running with current Python."
}

Set-Location $repoRoot
python -m unittest discover -s tests/ui -p "test_*.py"
python -m unittest discover -s tests/backend -p "test_*.py"
python -m unittest discover -s tests/integration -p "test_*.py"
python -m unittest discover -s tests/quality -p "test_*.py"
