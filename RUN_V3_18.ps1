$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python .\dashboard\patch_strategy_improvement_api_v3_18.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python .\dashboard\patch_strategy_improvement_ui_v3_18.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m py_compile .\dashboard\strategy_improvement_candidates_v3_18.py .\dashboard\trade_analytics_v3_5.py .\dashboard\verify_strategy_improvement_utf8_v3_18.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m unittest .\tests\test_strategy_improvement_candidates_v3_18.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
