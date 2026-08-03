
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_05_to_v83_08.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_local_action_dispatcher_v83_05_to_v83_08 `
  -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_05_TO_V83_08_LOCAL_ACTION_DISPATCHER.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python tools/verify_local_action_dispatcher_v83_05_to_v83_08.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V83.05-V83.08 TEST AND VERIFY PASS"
