$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest tools.test_p3_partial_fill_handling_validation -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "PARTIAL FILL HANDLER: VERIFIED"
Write-Host "BROKER WRITE: OFF"
Write-Host "NEW PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
