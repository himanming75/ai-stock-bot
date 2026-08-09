$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

if(-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY){
 Write-Host "WAITING_FOR_ALPACA_MARKET_DATA_CREDENTIALS"
 exit 3
}

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.eligible_signal_to_sandbox_cli_v2_1_10 `
 --root C:\stock-bot `
 --symbols AAPL MSFT SPY `
 --bootstrap-bars 3 `
 --quantity 1 `
 --cooldown-seconds 30
