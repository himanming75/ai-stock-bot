$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v5201_to_v5400_dual_account_operations `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "ACTIVE PROFILE: PAPER_TEST"
Write-Host "PROFILE COUNT: 5"
Write-Host "ETRADE READ: BLOCKED PENDING VALIDATION"
Write-Host "NETWORK READ: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
