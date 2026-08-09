$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

Write-Host "=== BROKER INTEGRATION V2.1 DEVELOPMENT ==="

& $Python .\dashboard\patch_etrade_sandbox_order_status_v2_1.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_etrade_sandbox_order_ui_v2_1.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\test_etrade_sandbox_order_v2_1.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\tests\run_etrade_sandbox_order_fixture_v2_1.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
