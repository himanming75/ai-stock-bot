$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

Write-Host "=== V2.5 REGIME-AWARE BUY NET-COST LIFECYCLE AUDIT ==="

& $Python .\tools\audit_regime_aware_buy_v2_5.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
