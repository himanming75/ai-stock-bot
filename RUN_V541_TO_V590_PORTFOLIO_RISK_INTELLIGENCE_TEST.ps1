$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest `
    tools.test_v541_to_v590_portfolio_risk_intelligence `
    -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "MARKET NETWORK: OFF"
Write-Host "BROKER NETWORK: OFF"
Write-Host "ORDER TICKET: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
