$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

Write-Host "=== V3.10 CANONICAL TRADE DETAIL + FILTERS ==="

& $Python .\dashboard\patch_trade_detail_api_v3_10.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_trade_detail_ui_v3_10.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile `
 .\dashboard\trade_analytics_v3_5.py `
 .\dashboard\patch_trade_detail_api_v3_10.py `
 .\dashboard\patch_trade_detail_ui_v3_10.py `
 .\dashboard\verify_trade_detail_utf8_v3_10.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m unittest .\tests\test_trade_detail_filters_v3_10.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
