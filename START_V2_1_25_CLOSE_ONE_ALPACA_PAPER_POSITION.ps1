$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "V2.1.25 ONE ALPACA PAPER POSITION EXIT"
Write-Host "This CAN close one existing Alpaca Paper position."
Write-Host "Live trading remains LOCKED."
Write-Host ""

$Confirm=Read-Host "Type CLOSE_ALPACA_PAPER_POSITION_ONCE"
if($Confirm -ne "CLOSE_ALPACA_PAPER_POSITION_ONCE"){
 throw "PAPER EXIT CANCELLED"
}

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
 throw "NON-PAPER ENDPOINT BLOCKED"
}

$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.alpaca_paper_exit_execution_recovery_cli_v2_1_25 `
 --root C:\stock-bot `
 --execute `
 --confirmation CLOSE_ALPACA_PAPER_POSITION_ONCE
