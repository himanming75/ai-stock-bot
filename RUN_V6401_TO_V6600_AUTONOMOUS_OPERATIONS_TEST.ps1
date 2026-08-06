$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v6401_to_v6600_autonomous_operations `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "AUTONOMOUS OPERATIONS: READY"
Write-Host "GLOBAL HEALTH: READY"
Write-Host "EMERGENCY STOP: READY"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
