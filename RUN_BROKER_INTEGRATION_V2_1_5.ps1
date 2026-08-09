$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

Write-Host "=== BROKER INTEGRATION V2.1.5 DEVELOPMENT ==="

& $Python .\dashboard\patch_etrade_ai_signal_decision_status_v2_1_5.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_etrade_ai_signal_decision_ui_v2_1_5.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== UNIT TESTS ==="
& $Python .\tests\test_etrade_ai_signal_decision_v2_1_5.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== SYNTHETIC SIGNAL DECISION ==="
& $Python .\tests\run_etrade_ai_signal_decision_fixture_v2_1_5.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
