$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "V2.1.30 READ-ONLY RECOVERY RECONCILIATION"
Write-Host "Alpaca Paper broker reads only. No order submission."
Write-Host "Live trading remains LOCKED."

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper
if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
 throw "NON-PAPER ENDPOINT BLOCKED"
}

$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -m broker_integration_v1.session_crash_network_restart_recovery_cli_v2_1_30 --root C:\stock-bot --reconcile
