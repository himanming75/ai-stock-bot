
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_25_to_v83_28.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_automatic_schedule_evaluation_v83_25_to_v83_28 `
  -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_25_TO_V83_28_AUTOMATIC_SCHEDULE_EVALUATION.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python tools/verify_automatic_schedule_evaluation_v83_25_to_v83_28.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V83.25-V83.28 TEST AND VERIFY PASS"
