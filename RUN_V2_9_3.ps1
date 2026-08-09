$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "=== V2.9.3 RUN ==="

powershell -NoProfile -ExecutionPolicy Bypass -File .\RECOVER_V2_9_3.ps1
if($LASTEXITCODE -ne 0){throw "V2.9.3 STALE LOCK RECOVERY FAILED"}

Write-Host ""
Write-Host "=== V2.9.2 READINESS RE-AUDIT ==="

powershell -NoProfile -ExecutionPolicy Bypass -File .\AUDIT_V2_9_2.ps1
if($LASTEXITCODE -ne 0){throw "V2.9.2 READINESS RE-AUDIT FAILED"}

Write-Host "RUN: PASS"
