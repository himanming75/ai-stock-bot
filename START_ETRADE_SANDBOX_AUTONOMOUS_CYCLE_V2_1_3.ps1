$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

if(-not $env:ETRADE_CONSUMER_KEY -or -not $env:ETRADE_CONSUMER_SECRET){
 Write-Host "WAITING_FOR_CREDENTIALS"
 exit 3
}

Write-Host "===================================================="
Write-Host " E*TRADE SANDBOX AUTONOMOUS CYCLE V2.1.3"
Write-Host "===================================================="
Write-Host "ONE CYCLE ONLY"
Write-Host "Sandbox only"
Write-Host "Auto repeat disabled"
Write-Host "PROD orders locked"
Write-Host ""

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.etrade_sandbox_autonomous_cycle_cli_v2_1_3 `
 --root C:\stock-bot `
 --network
