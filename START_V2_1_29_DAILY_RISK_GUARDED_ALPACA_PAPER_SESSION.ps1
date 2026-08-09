$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
Write-Host "V2.1.29 DAILY RISK-GUARDED ALPACA PAPER SESSION"
Write-Host "Policy: max 2 completed round-trips/day, max $5 fill-based daily loss, max 2 consecutive losses."
Write-Host "Live trading remains LOCKED."
$Confirm=Read-Host "Type RUN_DAILY_RISK_GUARDED_ALPACA_PAPER_SESSION"
if($Confirm -ne "RUN_DAILY_RISK_GUARDED_ALPACA_PAPER_SESSION"){throw "SESSION CANCELLED"}
. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper
if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){throw "NON-PAPER ENDPOINT BLOCKED"}
$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -m broker_integration_v1.daily_risk_budget_kill_switch_cli_v2_1_29 --root C:\stock-bot --mode PAPER --confirmation RUN_DAILY_RISK_GUARDED_ALPACA_PAPER_SESSION --max-round-trips 2 --interval-seconds 30
