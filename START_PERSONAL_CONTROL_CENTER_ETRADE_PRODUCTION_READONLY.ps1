$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo

if(-not $env:ETRADE_CONSUMER_KEY -or -not $env:ETRADE_CONSUMER_SECRET){
    Write-Host "WAITING_FOR_ETRADE_CONSUMER_CREDENTIALS"
    Write-Host ""
    Write-Host 'Set these in THIS PowerShell window first:'
    Write-Host '$env:ETRADE_CONSUMER_KEY="YOUR_KEY"'
    Write-Host '$env:ETRADE_CONSUMER_SECRET="YOUR_SECRET"'
    exit 3
}

Write-Host "Starting E*TRADE Production READ-ONLY OAuth session..."
Write-Host "No order submission. No token persistence."

& "$Repo\.venv\Scripts\python.exe" `
  "$Repo\tools\start_personal_control_center_etrade_readonly.py" `
  --host 127.0.0.1 `
  --port 8767

exit $LASTEXITCODE
