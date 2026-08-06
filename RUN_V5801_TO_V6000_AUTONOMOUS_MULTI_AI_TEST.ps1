$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v5801_to_v6000_autonomous_multi_ai `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "MULTI AI VOTING: READY"
Write-Host "CHAMPION CHALLENGER: READY"
Write-Host "AUTOMATIC PROMOTION: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
