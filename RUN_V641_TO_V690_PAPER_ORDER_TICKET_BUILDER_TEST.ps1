$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest `
    tools.test_v641_to_v690_paper_order_ticket_builder `
    -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "BROKER NETWORK: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER SUBMISSION: OFF"
Write-Host "LIVE SUBMISSION: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
