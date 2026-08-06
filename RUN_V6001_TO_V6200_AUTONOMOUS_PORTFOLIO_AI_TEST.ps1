$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v6001_to_v6200_autonomous_portfolio_ai `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "AUTONOMOUS PORTFOLIO AI: READY"
Write-Host "RISK ALLOCATION: READY"
Write-Host "AUTOMATIC REBALANCE: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
