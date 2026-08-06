$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
  tools.test_v8201_to_v8400_broker_abstraction `
  -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "BROKER FACTORY: READY"
Write-Host "UNIVERSAL MODELS: READY"
Write-Host "ALPACA ADAPTER: READY"
Write-Host "ETRADE ADAPTER: READY"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
Write-Host "ORDER CANCEL: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
