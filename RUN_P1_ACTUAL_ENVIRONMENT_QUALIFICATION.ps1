$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Project virtual environment was not found: $Python"
}

$ImportScript = Join-Path $Root "IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1"
if (-not (Test-Path $ImportScript)) {
    throw "Credential import script was not found."
}

Write-Host "=== P1 LOAD PAPER CREDENTIAL ENVIRONMENT ==="
. $ImportScript -Mode paper

Write-Host "=== P1 ACTUAL ENVIRONMENT QUALIFICATION ==="
$env:PYTHONPATH = $Root
& $Python (
    Join-Path $Root `
    "tools\run_p1_actual_environment_qualification.py"
)
exit $LASTEXITCODE
