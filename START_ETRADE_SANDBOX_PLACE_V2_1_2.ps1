$ErrorActionPreference="Stop"

Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

if(-not $env:ETRADE_CONSUMER_KEY -or -not $env:ETRADE_CONSUMER_SECRET){
 Write-Host "WAITING_FOR_CREDENTIALS"
 exit 3
}

Write-Host "===================================================="
Write-Host " E*TRADE SANDBOX PLACE V2.1.2"
Write-Host "===================================================="
Write-Host "Sandbox only."
Write-Host "No real money or securities."
Write-Host "The program will Preview first."
Write-Host "It will Place only if you type PLACE."
Write-Host "PROD orders remain LOCKED."
Write-Host ""

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.etrade_sandbox_place_ledger_cli_v2_1_2 `
 --root C:\stock-bot `
 --network
