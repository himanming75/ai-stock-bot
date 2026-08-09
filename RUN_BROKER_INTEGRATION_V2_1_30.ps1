$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"
$Python="C:\stock-bot\.venv\Scripts\python.exe"

Write-Host "=== BROKER INTEGRATION V2.1.30 ==="

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_session_crash_network_restart_recovery_v2_1_30.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
