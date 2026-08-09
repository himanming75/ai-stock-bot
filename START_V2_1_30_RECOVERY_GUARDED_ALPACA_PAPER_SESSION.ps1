$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "V2.1.30 RECOVERY-GUARDED ALPACA PAPER SESSION"
Write-Host "Startup broker reconciliation is read-only."
Write-Host "If recovery is safe, existing V2.1.29 controls Paper trading."
Write-Host "Live trading remains LOCKED."

$Confirm=Read-Host "Type RUN_RECOVERY_GUARDED_ALPACA_PAPER_SESSION"
if($Confirm -ne "RUN_RECOVERY_GUARDED_ALPACA_PAPER_SESSION"){
 throw "RECOVERY PAPER SESSION CANCELLED"
}

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper
if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
 throw "NON-PAPER ENDPOINT BLOCKED"
}

$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -m broker_integration_v1.session_crash_network_restart_recovery_cli_v2_1_30 --root C:\stock-bot --mode PAPER --confirmation RUN_RECOVERY_GUARDED_ALPACA_PAPER_SESSION --max-round-trips 2 --interval-seconds 30
