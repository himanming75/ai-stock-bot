$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v139_10.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_terminal_commit_cycle_completion_v139_10 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_V139_10_TERMINAL_COMMIT_CYCLE_COMPLETION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_terminal_commit_cycle_completion_v139_10.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.10 TEST AND VERIFY PASS"
