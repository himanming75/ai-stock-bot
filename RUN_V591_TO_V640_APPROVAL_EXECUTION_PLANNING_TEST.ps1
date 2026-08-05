$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest `
    tools.test_v591_to_v640_approval_execution_planning `
    -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "BROKER NETWORK: OFF"
Write-Host "ORDER TICKET: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
