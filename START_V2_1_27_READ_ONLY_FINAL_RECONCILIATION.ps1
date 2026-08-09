$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "V2.1.27 READ-ONLY FINAL EXIT FILL RECONCILIATION"
Write-Host "Alpaca Paper READS only."
Write-Host "No order submission from this stage."
Write-Host "Live trading remains LOCKED."
Write-Host ""

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
 throw "NON-PAPER ENDPOINT BLOCKED"
}

$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.final_exit_fill_reconciliation_round_trip_cli_v2_1_27 `
 --root C:\stock-bot `
 --reconcile `
 --interval-seconds 5 `
 --max-cycles 12
