$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
Write-Host "=== V3.5 HISTORICAL PERFORMANCE & TRADE ANALYTICS ==="
& $Python .\dashboard\patch_v3_5_server.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python .\dashboard\patch_v3_5_html.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m py_compile .\dashboard\operations_dashboard_v3_2.py .\dashboard\visualization_v3_4.py .\dashboard\trade_analytics_v3_5.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m unittest .\tests\test_trade_analytics_v3_5.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
