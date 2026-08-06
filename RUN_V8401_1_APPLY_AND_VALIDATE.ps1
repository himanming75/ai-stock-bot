$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\RUN_V8401_1_ORDERS_NORMALIZATION_HOTFIX_TEST.ps1

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\RUN_ACTUAL_MULTI_BROKER_SYNC_READ_ONLY.ps1

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "V8401.1 HOTFIX: PASS"
Write-Host "ACTUAL MULTI BROKER SYNC: PASS"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
Write-Host "ORDER CANCEL: OFF"
