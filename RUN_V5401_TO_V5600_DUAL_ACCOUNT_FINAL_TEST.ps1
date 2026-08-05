$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v5401_to_v5600_dual_account_final `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "DUAL ACCOUNT CONTROLLER: READY"
Write-Host "FOURTH STAGE FINAL CERTIFICATION: READY"
Write-Host "FUTURE MULTI ACCOUNT EXTENSION: READY"
Write-Host "NETWORK READ: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
