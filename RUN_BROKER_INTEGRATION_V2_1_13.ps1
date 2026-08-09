$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

Write-Host "=== BROKER INTEGRATION V2.1.13 ==="

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_persistent_market_observer_v2_1_13.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\run_persistent_market_observer_fixture_v2_1_13.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
