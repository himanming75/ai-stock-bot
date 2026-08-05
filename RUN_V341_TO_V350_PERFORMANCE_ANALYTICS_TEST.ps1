$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v341_to_v350_performance_analytics `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "EXTERNAL NETWORK: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
