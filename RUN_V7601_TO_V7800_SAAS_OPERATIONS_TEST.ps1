$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v7601_to_v7800_saas_operations `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "SAAS OPERATIONS: READY"
Write-Host "OBSERVABILITY: READY"
Write-Host "NOTIFICATION QUEUE: READY"
Write-Host "BACKUP AND RESTORE DRY RUN: READY"
Write-Host "EXTERNAL NOTIFICATIONS: OFF"
Write-Host "SERVICE RESTART: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
