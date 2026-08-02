$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_op2_17_to_op2_20.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_shadow_daily_automation_op2_17_to_op2_20 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_OP2_17_TO_OP2_20_SHADOW_DAILY_AUTOMATION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_shadow_daily_automation_op2_17_to_op2_20.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OP2.17-OP2.20 TEST AND VERIFY PASS"
