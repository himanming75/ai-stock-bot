$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/install_check_v139_06.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m unittest tools.test_next_order_eligibility_v139_06 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell -ExecutionPolicy Bypass -File .\RUN_V139_06_NEXT_ORDER_ELIGIBILITY.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_next_order_eligibility_v139_06.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V139.06 TEST AND VERIFY PASS"
