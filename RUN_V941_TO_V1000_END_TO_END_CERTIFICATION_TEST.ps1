$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest `
    tools.test_v941_to_v1000_end_to_end_certification `
    -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
