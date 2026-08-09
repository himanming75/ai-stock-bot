$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "V2.1.28 CONTINUOUS BOUNDED ALPACA PAPER SESSION"
Write-Host "Reuses V2.1.26 + V2.1.27."
Write-Host "Maximum completed round-trips this session: 2"
Write-Host "Existing Paper entry/exit guards remain enforced."
Write-Host "Live trading remains LOCKED."
Write-Host ""

$Confirm=Read-Host "Type RUN_BOUNDED_CONTINUOUS_ALPACA_PAPER_SESSION"
if($Confirm -ne "RUN_BOUNDED_CONTINUOUS_ALPACA_PAPER_SESSION"){
 throw "CONTINUOUS PAPER SESSION CANCELLED"
}

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
 throw "NON-PAPER ENDPOINT BLOCKED"
}

$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.continuous_bounded_paper_session_cli_v2_1_28 `
 --root C:\stock-bot `
 --mode PAPER `
 --confirmation RUN_BOUNDED_CONTINUOUS_ALPACA_PAPER_SESSION `
 --max-round-trips 2 `
 --max-supervisor-cycles 40 `
 --interval-seconds 30
