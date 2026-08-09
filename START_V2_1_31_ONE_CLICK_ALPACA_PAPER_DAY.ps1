$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "V2.1.31 ONE-CLICK DAILY ALPACA PAPER OPERATION"
Write-Host "Startup recovery: V2.1.30"
Write-Host "Daily risk: V2.1.29"
Write-Host "Continuous round-trip: V2.1.28"
Write-Host "Market wait: Alpaca Paper READ-ONLY"
Write-Host "Maximum completed round-trips/day: existing V2.1.29 policy"
Write-Host "Live trading remains LOCKED."
Write-Host ""

$Confirm=Read-Host "Type RUN_ONE_CLICK_DAILY_ALPACA_PAPER_OPERATION"
if($Confirm -ne "RUN_ONE_CLICK_DAILY_ALPACA_PAPER_OPERATION"){
 throw "ONE-CLICK PAPER DAY CANCELLED"
}

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
 throw "NON-PAPER ENDPOINT BLOCKED"
}

$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.one_click_daily_paper_operation_cli_v2_1_31 `
 --root C:\stock-bot `
 --paper `
 --confirmation RUN_ONE_CLICK_DAILY_ALPACA_PAPER_OPERATION
