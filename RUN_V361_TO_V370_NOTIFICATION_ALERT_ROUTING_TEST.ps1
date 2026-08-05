$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v361_to_v370_notification_alert_routing `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "NOTIFICATION SEND: OFF"
Write-Host "EXTERNAL NETWORK: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
