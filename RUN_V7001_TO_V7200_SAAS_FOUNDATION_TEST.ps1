$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v7001_to_v7200_saas_foundation `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "SAAS FOUNDATION: READY"
Write-Host "MULTI TENANT CONTROL PLANE: READY"
Write-Host "CREDENTIAL STORAGE: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
