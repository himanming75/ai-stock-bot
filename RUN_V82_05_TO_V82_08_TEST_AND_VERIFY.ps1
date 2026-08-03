
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v82_05_to_v82_08.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_shadow_scheduler_v82_05_to_v82_08 `
  -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V82_05_TO_V82_08_SHADOW_SCHEDULER.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python tools/verify_shadow_scheduler_v82_05_to_v82_08.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.05-V82.08 TEST AND VERIFY PASS"
