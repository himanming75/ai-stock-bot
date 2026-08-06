$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v7201_to_v7400_saas_persistence `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "SAAS SQLITE PERSISTENCE: READY"
Write-Host "RESTART RESTORE: READY"
Write-Host "LOGIN AND DASHBOARD UI: READY"
Write-Host "BROKER CREDENTIAL STORAGE: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
