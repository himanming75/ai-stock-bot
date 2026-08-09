$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "=== V2.9.2 RUN ==="
powershell -NoProfile -ExecutionPolicy Bypass -File .\AUDIT_V2_9_2.ps1
$Code=$LASTEXITCODE

if($Code -ne 0){
    Write-Host ""
    Write-Host "V2.9.2 found a runtime activation blocker. No task/runtime setting was changed."
    exit $Code
}

Write-Host "RUN: PASS"
