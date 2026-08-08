$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
Write-Host "=== V2.4 1D OPPOSITE BUY ROBUSTNESS AUDIT ==="
& $Python .\tools\audit_1d_opposite_buy_robustness_v2_4.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
