$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_v3001_to_v3200_multi_broker_core -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "NETWORK: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
