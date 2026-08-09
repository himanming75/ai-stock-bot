$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

Write-Host "=== BROKER INTEGRATION V2.1.8 ==="

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_historical_bootstrap_live_continuation_v2_1_8.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\run_historical_bootstrap_fixture_v2_1_8.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
