$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v139_09.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_active_order_lifecycle_monitor_v139_09 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_V139_09_ACTIVE_ORDER_LIFECYCLE_MONITOR.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_active_order_lifecycle_monitor_v139_09.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.09 TEST AND VERIFY PASS"
