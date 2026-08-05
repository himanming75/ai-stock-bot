$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v3601_to_v3800_etrade_oauth_session `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "FIXTURE OAUTH TRANSPORT: ON"
Write-Host "REAL ETRADE CREDENTIALS USED: NO"
Write-Host "SANDBOX NETWORK READ: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
