$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v139_02.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_terminal_commit_handoff_v139_02 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_V139_02_TERMINAL_COMMIT_HANDOFF.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_terminal_commit_handoff_v139_02.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.02 TEST AND VERIFY PASS"
