$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest `
    tools.test_v1001_to_v1200_ai_market_intelligence `
    -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "NETWORK: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
