$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v82_01_to_v82_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_autonomous_shadow_cycle_v82_01_to_v82_04 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V82_01_TO_V82_04_AUTONOMOUS_SHADOW_CYCLE.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_autonomous_shadow_cycle_v82_01_to_v82_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V82.01-V82.04 TEST AND VERIFY PASS"
