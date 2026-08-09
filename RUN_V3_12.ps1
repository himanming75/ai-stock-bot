$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
Write-Host "=== V3.12 STRATEGY QUALITY + READINESS SCORE ==="
& $Python .\dashboard\patch_strategy_readiness_api_v3_12.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python .\dashboard\patch_strategy_readiness_ui_v3_12.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m py_compile .\dashboard\strategy_readiness_v3_12.py .\dashboard\trade_analytics_v3_5.py .\dashboard\verify_strategy_readiness_utf8_v3_12.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m unittest .\tests\test_strategy_readiness_v3_12.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
