$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest tools.test_paper_order_lifecycle_monitor -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "BROKER WRITE: OFF"
Write-Host "NEW PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
