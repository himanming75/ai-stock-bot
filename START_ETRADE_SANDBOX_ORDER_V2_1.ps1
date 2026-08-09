$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

if(-not $env:ETRADE_CONSUMER_KEY -or -not $env:ETRADE_CONSUMER_SECRET){
 Write-Host "WAITING_FOR_CREDENTIALS"
 exit 3
}

Write-Host "Preview only by default. No real money or securities move in Sandbox."
Write-Host "For Sandbox Place testing, add --place manually to the Python command."
C:\stock-bot\.venv\Scripts\python.exe -m broker_integration_v1.etrade_sandbox_order_cli_v2_1 --network
