$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
Write-Host "=== V2.0 BUY REJECTION FUNNEL AUDIT ==="
& $Python .\tools\audit_buy_rejection_funnel_v2_0.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
