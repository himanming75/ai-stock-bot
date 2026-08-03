
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_21_to_v83_24.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_scheduled_run_dispatch_v83_21_to_v83_24 `
  -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_21_TO_V83_24_SCHEDULED_RUN_DISPATCH.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python tools/verify_scheduled_run_dispatch_v83_21_to_v83_24.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V83.21-V83.24 TEST AND VERIFY PASS"
