$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

Write-Host "=== V2.6 REGIME-AWARE BUY WALK-FORWARD OOS ==="

& $Python .\tools\audit_regime_aware_buy_walkforward_oos_v2_6.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
