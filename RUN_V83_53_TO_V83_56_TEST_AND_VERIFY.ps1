$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_53_to_v83_56.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_retry_cycle_completion_v83_53_to_v83_56 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_53_TO_V83_56_RETRY_CYCLE_COMPLETION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_retry_cycle_completion_v83_53_to_v83_56.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.53-V83.56 TEST AND VERIFY PASS"
