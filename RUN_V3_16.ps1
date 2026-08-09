$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

Write-Host "=== V3.16 MARKET REGIME PERFORMANCE ANALYSIS ==="

& $Python .\dashboard\patch_market_regime_api_v3_16.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_market_regime_ui_v3_16.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile `
 .\dashboard\market_regime_analysis_v3_16.py `
 .\dashboard\trade_analytics_v3_5.py `
 .\dashboard\verify_market_regime_utf8_v3_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m unittest .\tests\test_market_regime_analysis_v3_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
