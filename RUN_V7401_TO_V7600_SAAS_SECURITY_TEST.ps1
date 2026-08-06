$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v7401_to_v7600_saas_security `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "SAAS SECURITY: READY"
Write-Host "ACCOUNT RECOVERY: READY"
Write-Host "MFA: READY"
Write-Host "ADMIN CONSOLE: READY"
Write-Host "EMAIL DELIVERY: OFF"
Write-Host "BROKER CREDENTIAL STORAGE: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
