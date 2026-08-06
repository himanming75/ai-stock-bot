$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
  tools.test_v8401_1_orders_normalization_hotfix `
  -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

python -m unittest `
  tools.test_v8401_to_v8600_broker_sync `
  -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "HOTFIX TEST: PASS"
Write-Host "MIXED ORDER TYPES: SAFE"
Write-Host "NESTED ETRADE ORDERS: SUPPORTED"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
Write-Host "ORDER CANCEL: OFF"
