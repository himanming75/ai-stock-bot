$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

Write-Host "=== BROKER INTEGRATION V2.1.16 ==="

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_fresh_eligible_signal_evidence_capture_v2_1_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\run_fresh_eligible_signal_evidence_fixture_v2_1_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
