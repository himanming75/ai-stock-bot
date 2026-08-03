$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_37_to_v83_40.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_trigger_chain_retry_policy_v83_37_to_v83_40 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_37_TO_V83_40_TRIGGER_CHAIN_RETRY_POLICY.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_trigger_chain_retry_policy_v83_37_to_v83_40.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.37-V83.40 TEST AND VERIFY PASS"
