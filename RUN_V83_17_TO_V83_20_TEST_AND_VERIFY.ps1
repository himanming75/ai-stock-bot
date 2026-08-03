
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_17_to_v83_20.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_scheduled_supervised_runner_v83_17_to_v83_20 `
  -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_17_TO_V83_20_SCHEDULED_SUPERVISED_RUNNER.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python tools/verify_scheduled_supervised_runner_v83_17_to_v83_20.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V83.17-V83.20 TEST AND VERIFY PASS"
