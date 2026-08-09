$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

Write-Host "=== BROKER INTEGRATION V2.1.4 DEVELOPMENT ==="

& $Python .\dashboard\patch_etrade_sandbox_bounded_multi_cycle_status_v2_1_4.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_etrade_sandbox_bounded_multi_cycle_ui_v2_1_4.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m compileall -q .\broker_integration_v1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== UNIT TESTS ==="
& $Python .\tests\test_etrade_sandbox_bounded_multi_cycle_v2_1_4.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== SYNTHETIC BOUNDED MULTI-CYCLE ==="
& $Python .\tests\run_etrade_sandbox_bounded_multi_cycle_fixture_v2_1_4.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
