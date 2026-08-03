
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_09_to_v83_12.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_controlled_automation_cycle_v83_09_to_v83_12 `
  -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_09_TO_V83_12_CONTROLLED_AUTOMATION_CYCLE.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python tools/verify_controlled_automation_cycle_v83_09_to_v83_12.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V83.09-V83.12 TEST AND VERIFY PASS"
