$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

Write-Host "=== V2.8.2 REPAIR EXACT PAPER LOOP SHADOW HOOK ==="
& $Python .\tools\repair_exact_paper_loop_shadow_v2_8_2.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host ""
Write-Host "=== COMPILE CHECK ==="
& $Python -m py_compile .\paper_daily_session\runner.py
if($LASTEXITCODE -ne 0){throw "RUNNER COMPILE FAILED"}

Write-Host "RUN: PASS"
