$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

if(-not $env:ETRADE_CONSUMER_KEY -or -not $env:ETRADE_CONSUMER_SECRET){
 Write-Host "WAITING_FOR_CREDENTIALS"
 exit 3
}

Write-Host "===================================================="
Write-Host " E*TRADE SANDBOX BOUNDED MULTI-CYCLE V2.1.4"
Write-Host "===================================================="
Write-Host "Maximum 3 cycles"
Write-Host "Cooldown 30 seconds"
Write-Host "Duplicate guard ON"
Write-Host "Kill switch supported"
Write-Host "PROD orders locked"
Write-Host ""

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.etrade_sandbox_bounded_multi_cycle_cli_v2_1_4 `
 --root C:\stock-bot `
 --network `
 --max-cycles 3 `
 --cooldown-seconds 30
