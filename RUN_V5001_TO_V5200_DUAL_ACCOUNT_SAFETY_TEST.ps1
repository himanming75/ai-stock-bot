$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v5001_to_v5200_dual_account_safety `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "ACTIVE ACCOUNTS: ALPACA PAPER + ETRADE PRIMARY"
Write-Host "FUTURE MULTI ACCOUNT EXTENSION: READY"
Write-Host "NETWORK READ: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
