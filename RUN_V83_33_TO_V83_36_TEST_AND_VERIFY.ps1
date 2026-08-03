$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_33_to_v83_36.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_trigger_recovery_dispatch_chain_v83_33_to_v83_36 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_33_TO_V83_36_TRIGGER_RECOVERY_DISPATCH_CHAIN.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_trigger_recovery_dispatch_chain_v83_33_to_v83_36.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.33-V83.36 TEST AND VERIFY PASS"
