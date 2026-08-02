$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v139_03.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_next_cycle_unlock_v139_03 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_V139_03_NEXT_CYCLE_UNLOCK.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_next_cycle_unlock_v139_03.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.03 TEST AND VERIFY PASS"
