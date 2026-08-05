$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v781_to_v860_paper_submit_engine `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "CREDENTIALS LOADED: NO"
Write-Host "NETWORK LIBRARY: NOT USED"
Write-Host "BROKER NETWORK: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER SUBMISSION: OFF"
Write-Host "LIVE SUBMISSION: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
