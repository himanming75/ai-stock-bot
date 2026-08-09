$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

Write-Host "=== V3.0 TWO-WEEK PAPER VALIDATION COORDINATOR ==="

& $Python .\tools\coordinate_two_week_paper_validation_v3_0.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
