$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

if(-not $env:ETRADE_CONSUMER_KEY -or -not $env:ETRADE_CONSUMER_SECRET){
 Write-Host "WAITING_FOR_CREDENTIALS"
 exit 3
}

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.etrade_sandbox_order_cli_v2_1 `
 --network
