$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

if(-not $env:ETRADE_CONSUMER_KEY -or -not $env:ETRADE_CONSUMER_SECRET){
 Write-Host "WAITING_FOR_CREDENTIALS"
 Write-Host 'Set in this PowerShell session:'
 Write-Host '$env:ETRADE_CONSUMER_KEY="your_key"'
 Write-Host '$env:ETRADE_CONSUMER_SECRET="your_secret"'
 exit 3
}

& $Python -m broker_integration_v1.etrade_readonly_oauth_cli_v2 --root C:\stock-bot --environment sandbox --network
