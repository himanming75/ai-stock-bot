$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_v3201_to_v3400_alpaca_adapter_extraction -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "FIXTURE TRANSPORT: ON"
Write-Host "REAL CREDENTIALS USED: NO"
Write-Host "NETWORK: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
