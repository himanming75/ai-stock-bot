$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

if(-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY){
 Write-Host "WAITING_FOR_ALPACA_MARKET_DATA_CREDENTIALS"
 exit 3
}

Write-Host "===================================================="
Write-Host " V2.1.8 HISTORICAL BOOTSTRAP + LIVE CONTINUATION"
Write-Host "===================================================="
Write-Host "Historical REST: READ-ONLY"
Write-Host "Live WebSocket continuation: OPTIONAL"
Write-Host "Broker orders: DISABLED"
Write-Host "PROD orders: LOCKED"
Write-Host "Live trading: LOCKED"
Write-Host ""

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.historical_bootstrap_live_continuation_cli_v2_1_8 `
 --symbols AAPL MSFT SPY `
 --bars-per-symbol 3 `
 --quantity 1
