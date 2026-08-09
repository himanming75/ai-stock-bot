$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

Write-Host "=== BROKER INTEGRATION V2.1.7 DEVELOPMENT ==="

& $Python .\dashboard\patch_etrade_current_market_data_signal_status_v2_1_7.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_etrade_current_market_data_signal_ui_v2_1_7.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== UNIT TESTS ==="
& $Python .\tests\test_etrade_current_market_data_signal_v2_1_7.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== SYNTHETIC CURRENT MARKET DATA PIPELINE ==="
& $Python .\tests\run_etrade_current_market_data_signal_fixture_v2_1_7.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
