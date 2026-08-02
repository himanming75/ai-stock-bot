$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/install_check_v139_11_to_v139_15.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m unittest tools.test_ultra_fast_cycle_finalization_v139_11_to_v139_15 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell -ExecutionPolicy Bypass -File .\RUN_V139_11_TO_V139_15_ULTRA_FAST.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_ultra_fast_cycle_finalization_v139_11_to_v139_15.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V139.11-V139.15 TEST AND VERIFY PASS"
