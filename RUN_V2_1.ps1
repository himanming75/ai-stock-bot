$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
Write-Host "=== V2.1 BUY/SELL RR SYMMETRY AUDIT ==="
& $Python .\tools\audit_buy_sell_rr_symmetry_v2_1.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "RUN: PASS"
