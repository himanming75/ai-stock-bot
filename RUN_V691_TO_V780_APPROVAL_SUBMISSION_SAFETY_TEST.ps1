$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v691_to_v780_approval_submission_safety `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "BROKER NETWORK: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER SUBMISSION: OFF"
Write-Host "LIVE SUBMISSION: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
