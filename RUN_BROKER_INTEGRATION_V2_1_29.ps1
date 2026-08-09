$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"
$Python="C:\stock-bot\.venv\Scripts\python.exe"
Write-Host "=== BROKER INTEGRATION V2.1.29 ==="
& $Python -m compileall -q .\broker_integration_v1
& $Python .\tests\test_daily_risk_budget_kill_switch_v2_1_29.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
