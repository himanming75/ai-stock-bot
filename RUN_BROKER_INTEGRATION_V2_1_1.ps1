$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

& $Python -m py_compile `
 .\broker_integration_v1\etrade_sandbox_order_transport_v2_1.py `
 .\broker_integration_v1\etrade_sandbox_order_cli_v2_1.py

if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_etrade_sandbox_preview_diagnostic_v2_1_1.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V2.1.1 RUN: PASS"
