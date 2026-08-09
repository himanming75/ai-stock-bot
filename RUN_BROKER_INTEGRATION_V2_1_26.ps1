$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

Write-Host "=== BROKER INTEGRATION V2.1.26 ==="

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_full_alpaca_paper_round_trip_cycle_v2_1_26.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
