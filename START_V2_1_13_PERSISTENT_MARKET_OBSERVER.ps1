$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

if(-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY){
 Write-Host "WAITING_FOR_ALPACA_MARKET_DATA_CREDENTIALS"
 exit 3
}

Write-Host "===================================================="
Write-Host " V2.1.13 PERSISTENT MARKET OBSERVER"
Write-Host "===================================================="
Write-Host "Default runtime: 30 observations, 60 sec interval"
Write-Host "Stops after 10 consecutive unchanged observations"
Write-Host "No E*TRADE OAuth"
Write-Host "No Sandbox Preview/Place"
Write-Host "PROD locked"
Write-Host "Live trading locked"
Write-Host ""

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.persistent_market_observer_cli_v2_1_13 `
 --root C:\stock-bot `
 --symbols AAPL MSFT SPY `
 --bootstrap-bars 3 `
 --quantity 1 `
 --max-iterations 30 `
 --interval-seconds 60 `
 --stop-after-unchanged 10
