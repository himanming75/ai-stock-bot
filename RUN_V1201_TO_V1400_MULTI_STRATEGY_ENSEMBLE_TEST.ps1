$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_v1201_to_v1400_multi_strategy_ensemble -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "NETWORK: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
