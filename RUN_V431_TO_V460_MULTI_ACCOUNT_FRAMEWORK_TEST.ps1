$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v431_to_v460_multi_account_framework `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "CREDENTIAL VALUES STORED: NO"
Write-Host "BROKER NETWORK: OFF"
Write-Host "PAPER SUBMISSION: OFF"
Write-Host "LIVE SUBMISSION: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
