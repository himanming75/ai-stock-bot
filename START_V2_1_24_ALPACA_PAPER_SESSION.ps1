$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "V2.1.24 ALPACA PAPER INTRADAY SESSION"
Write-Host "This CAN submit at most one Alpaca Paper entry order."
Write-Host "Automatic exit orders remain DISABLED."
Write-Host "Live trading remains LOCKED."
Write-Host ""

$Confirm=Read-Host "Type RUN_ALPACA_PAPER_SESSION"
if($Confirm -ne "RUN_ALPACA_PAPER_SESSION"){
 throw "PAPER SESSION CANCELLED"
}

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
 throw "NON-PAPER ENDPOINT BLOCKED"
}

$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.paper_intraday_autonomous_session_cli_v2_1_24 `
 --root C:\stock-bot `
 --mode PAPER `
 --session-confirmation RUN_ALPACA_PAPER_SESSION `
 --max-cycles 20 `
 --interval-seconds 30 `
 --lifecycle-cycles 12
