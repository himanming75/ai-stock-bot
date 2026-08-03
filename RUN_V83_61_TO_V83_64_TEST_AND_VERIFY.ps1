$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_61_to_v83_64.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_crash_recovery_restart_continuation_v83_61_to_v83_64 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_61_TO_V83_64_CRASH_RECOVERY_RESTART_CONTINUATION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools\verify_crash_recovery_restart_continuation_v83_61_to_v83_64.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.61-V83.64 TEST AND VERIFY PASS"
