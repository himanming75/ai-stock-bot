$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"
Write-Host "=== BROKER INTEGRATION V2.1.21 ==="
& $Python -m compileall -q .\broker_integration_v1
& $Python .\tests\test_actual_intraday_canonical_e2e_v2_1_21.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
