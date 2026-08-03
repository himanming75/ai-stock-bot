$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_29_to_v83_32.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_local_trigger_dispatcher_v83_29_to_v83_32 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_29_TO_V83_32_LOCAL_TRIGGER_DISPATCHER.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_local_trigger_dispatcher_v83_29_to_v83_32.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.29-V83.32 TEST AND VERIFY PASS"
