$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

powershell -NoProfile -ExecutionPolicy Bypass -File .\CLEANUP_V2_9_1.ps1
if($LASTEXITCODE -ne 0){throw "V2.9.1 CLEANUP FAILED"}

Write-Host ""
Write-Host "=== V2.9 CERTIFICATION RETRY ==="
& $Python .\tools\certify_runtime_shadow_v2_9.py --root C:\stock-bot
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "RUN: PASS"
