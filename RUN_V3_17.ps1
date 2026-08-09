$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python=if(Test-Path ".\.venv\Scripts\python.exe"){
 ".\.venv\Scripts\python.exe"
}else{
 "python"
}

Write-Host "=== V3.17 STRATEGY WEAKNESS MAP ==="

& $Python .\dashboard\patch_strategy_weakness_api_v3_17.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python .\dashboard\patch_strategy_weakness_ui_v3_17.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m py_compile `
 .\dashboard\strategy_weakness_map_v3_17.py `
 .\dashboard\trade_analytics_v3_5.py `
 .\dashboard\verify_strategy_weakness_utf8_v3_17.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

& $Python -m unittest .\tests\test_strategy_weakness_map_v3_17.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
