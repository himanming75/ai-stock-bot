$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v139_07.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_autonomous_paper_order_launch_v139_07 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_V139_07_AUTONOMOUS_PAPER_ORDER_LAUNCH.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_autonomous_paper_order_launch_v139_07.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.07 TEST AND VERIFY PASS"
