$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
Write-Host "=== V3.11 CANONICAL PERFORMANCE DIAGNOSTICS ==="
& $Python .\dashboard\patch_performance_diagnostics_api_v3_11.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python .\dashboard\patch_performance_diagnostics_ui_v3_11.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m py_compile .\dashboard\performance_diagnostics_v3_11.py .\dashboard\trade_analytics_v3_5.py .\dashboard\verify_performance_diagnostics_utf8_v3_11.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m unittest .\tests\test_performance_diagnostics_v3_11.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
