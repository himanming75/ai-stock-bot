$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
Write-Host "=== V1.9 PRE-THRESHOLD BUY RECOVERY COUNTERFACTUAL ==="
& $Python .\tools\analyze_pre_threshold_buy_recovery_v1_9.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
