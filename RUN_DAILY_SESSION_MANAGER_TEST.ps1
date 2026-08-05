$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest tools.test_daily_session_manager -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "AUTORUN REGISTRATION: NOT PERFORMED"
Write-Host "WATCHDOG LAUNCH: NOT PERFORMED"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
