$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python=if(Test-Path ".\.venv\Scripts\python.exe"){
 ".\.venv\Scripts\python.exe"
}else{
 "python"
}

Write-Host "=== V3.15 STRATEGY ROBUSTNESS + FAILURE BOUNDARY ==="

& $Python .\dashboard\patch_strategy_robustness_api_v3_15.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_strategy_robustness_ui_v3_15.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile `
 .\dashboard\strategy_robustness_v3_15.py `
 .\dashboard\trade_analytics_v3_5.py `
 .\dashboard\verify_strategy_robustness_utf8_v3_15.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m unittest .\tests\test_strategy_robustness_v3_15.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
