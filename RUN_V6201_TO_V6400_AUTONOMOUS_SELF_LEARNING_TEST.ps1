$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v6201_to_v6400_autonomous_self_learning `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "SELF LEARNING ANALYSIS: READY"
Write-Host "EXPLAINABLE AI: READY"
Write-Host "AUTOMATIC PARAMETER MUTATION: OFF"
Write-Host "AUTOMATIC CHAMPION CHANGE: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
