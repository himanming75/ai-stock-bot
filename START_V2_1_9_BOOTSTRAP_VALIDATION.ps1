$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

if(-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY){
 Write-Host "WAITING_FOR_ALPACA_MARKET_DATA_CREDENTIALS"
 exit 3
}

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.bootstrap_live_continuity_cli_v2_1_9 `
 --symbols AAPL MSFT SPY `
 --bootstrap-bars 3 `
 --quantity 1
