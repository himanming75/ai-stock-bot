$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_v491_to_v540_ai_decision_engine -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "AI NETWORK: OFF"
Write-Host "MARKET NETWORK: OFF"
Write-Host "BROKER NETWORK: OFF"
Write-Host "ORDER TICKET: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
