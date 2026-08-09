$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "V2.1.26 FULL ALPACA PAPER ROUND-TRIP CYCLE"
Write-Host "This CAN submit one Alpaca Paper entry and one Alpaca Paper exit."
Write-Host "Existing V2.1.22/V2.1.25 guards remain enforced."
Write-Host "Live trading remains LOCKED."
Write-Host ""

$Confirm=Read-Host "Type RUN_FULL_ALPACA_PAPER_CYCLE"
if($Confirm -ne "RUN_FULL_ALPACA_PAPER_CYCLE"){
 throw "FULL PAPER CYCLE CANCELLED"
}

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
 throw "NON-PAPER ENDPOINT BLOCKED"
}

$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.full_alpaca_paper_round_trip_cli_v2_1_26 `
 --root C:\stock-bot `
 --mode PAPER `
 --confirmation RUN_FULL_ALPACA_PAPER_CYCLE `
 --max-cycles 20 `
 --interval-seconds 30 `
 --lifecycle-cycles 12
