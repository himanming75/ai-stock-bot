[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if(Test-Path ".\.venv\Scripts\python.exe") {
    $Python = ".\.venv\Scripts\python.exe"
}
else {
    $Python = "python"
}

Write-Host "=== MARKET OPEN AUTO VALIDATION ==="
Write-Host "BROKER: ALPACA PAPER ONLY"
Write-Host "MAXIMUM VALIDATION ORDERS: 1"
Write-Host "ETRADE LIVE WRITE: OFF"
Write-Host "LIVE ORDERS: 0"

& $Python .\tools\run_market_open_auto_validation.py `
    --repository-root $PSScriptRoot `
    --poll-seconds 30 `
    --timeout-minutes 480

exit $LASTEXITCODE
