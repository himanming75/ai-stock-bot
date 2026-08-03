$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_57_to_v83_60.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_full_schedule_completion_orchestrator_v83_57_to_v83_60 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_57_TO_V83_60_FULL_SCHEDULE_COMPLETION_ORCHESTRATOR.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_full_schedule_completion_orchestrator_v83_57_to_v83_60.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.57-V83.60 TEST AND VERIFY PASS"
