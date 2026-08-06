$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
  tools.test_v8401_to_v8600_broker_sync `
  -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "BROKER SYNC: READY"
Write-Host "RECONCILIATION: READY"
Write-Host "PORTAL SNAPSHOT: READY"
Write-Host "PARTIAL SUCCESS: READY"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
Write-Host "ORDER CANCEL: OFF"
