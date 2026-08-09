$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
Write-Host "=== V3.13 READINESS HISTORY + EVIDENCE TREND ==="
& $Python .\dashboard\patch_readiness_history_api_v3_13.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python .\dashboard\patch_readiness_history_ui_v3_13.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m py_compile .\dashboard\readiness_history_v3_13.py .\dashboard\trade_analytics_v3_5.py .\dashboard\verify_readiness_history_utf8_v3_13.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Python -m unittest .\tests\test_readiness_history_v3_13.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
