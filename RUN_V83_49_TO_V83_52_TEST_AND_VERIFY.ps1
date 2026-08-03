$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v83_49_to_v83_52.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_supervised_reentry_runner_v83_49_to_v83_52 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_49_TO_V83_52_SUPERVISED_REENTRY_RUNNER.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_supervised_reentry_runner_v83_49_to_v83_52.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.49-V83.52 TEST AND VERIFY PASS"
