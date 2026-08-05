$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Project virtual environment was not found: $Python"
}

$env:PYTHONPATH = $Root

Write-Host "=== P1 UNIT TEST ==="
& $Python -m unittest `
  tools.test_p1_actual_environment_qualification -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "=== P1 ACTUAL ENVIRONMENT QUALIFICATION ==="
& (Join-Path $Root "RUN_P1_ACTUAL_ENVIRONMENT_QUALIFICATION.ps1")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "=== P1 VERIFY ==="
& $Python (
    Join-Path $Root `
    "tools\verify_p1_actual_environment_qualification.py"
)
exit $LASTEXITCODE
