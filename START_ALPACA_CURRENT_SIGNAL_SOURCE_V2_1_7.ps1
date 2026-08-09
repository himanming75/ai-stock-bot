$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

if(-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY){
 Write-Host "WAITING_FOR_ALPACA_MARKET_DATA_CREDENTIALS"
 exit 3
}

Write-Host "===================================================="
Write-Host " V2.1.7 ALPACA CURRENT READ-ONLY MARKET DATA"
Write-Host "===================================================="
Write-Host "Read-only market data only"
Write-Host "No broker order submission"
Write-Host "PROD orders locked"
Write-Host "Live trading locked"
Write-Host ""

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.etrade_current_market_data_signal_cli_v2_1_7 `
 --symbols AAPL SPY MSFT `
 --bars-per-symbol 3 `
 --timeout-seconds 900 `
 --quantity 1 `
 --confirm "CONNECT READ ONLY ALPACA CURRENT MARKET DATA"
