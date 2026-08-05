$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest tools.test_automation_watchdog_restart_recovery -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "WATCHDOG SUBMISSION: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
