$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

& $Python -m py_compile `
 .\broker_integration_v1\alpaca_readonly_historical_bootstrap_v2_1_8.py `
 .\broker_integration_v1\historical_bootstrap_diagnostic_status_v2_1_8_1.py

if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_historical_bootstrap_diagnostic_v2_1_8_1.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V2.1.8.1 RUN: PASS"
