$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

Write-Host "=== V2.1.7.1 MARKET WAIT DIAGNOSTIC REPAIR ==="

& $Python -m py_compile `
 .\broker_integration_v1\alpaca_readonly_current_bar_collector_v2_1_7.py `
 .\broker_integration_v1\etrade_current_market_wait_diagnostic_status_v2_1_7_1.py

if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_market_wait_diagnostic_v2_1_7_1.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V2.1.7.1 RUN: PASS"
