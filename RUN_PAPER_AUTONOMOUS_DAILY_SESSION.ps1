[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)) {
    throw "PROJECT VIRTUAL ENVIRONMENT PYTHON NOT FOUND"
}

$env:APCA_API_KEY_ID = [Environment]::GetEnvironmentVariable("APCA_API_KEY_ID","User")
$env:APCA_API_SECRET_KEY = [Environment]::GetEnvironmentVariable("APCA_API_SECRET_KEY","User")

if(
    [string]::IsNullOrWhiteSpace($env:APCA_API_KEY_ID) -or
    [string]::IsNullOrWhiteSpace($env:APCA_API_SECRET_KEY)
) {
    throw "ALPACA PAPER CREDENTIALS ARE MISSING"
}

$env:LIVE_TRADING_ENABLED = "false"
$env:ETRADE_LIVE_WRITE_ENABLED = "false"
$env:ETRADE_LIVE_SUBMISSION_ENABLED = "false"
$env:BROKER_WRITE_ENABLED = "false"

$Today = (Get-Date).Date
$DateKey = $Today.ToString("yyyy-MM-dd")

$Tier5Dates = @("2026-08-07","2026-08-10","2026-08-11")
$Tier10Dates = @("2026-08-12","2026-08-13","2026-08-14")

if($Tier5Dates -contains $DateKey) {
    $MaximumDailyOrders = 5
}
elseif($Tier10Dates -contains $DateKey) {
    $MaximumDailyOrders = 10
}
elseif($Today -ge [datetime]"2026-08-17") {
    $MaximumDailyOrders = 15
}
else {
    $MaximumDailyOrders = 1
}

$MaximumOrderNotional = 100
$PollSeconds = 60
$CloseBufferMinutes = 15

$AuditDir = Join-Path $PSScriptRoot "runtime\paper_autotrading_ramp_v2"
New-Item -ItemType Directory -Path $AuditDir -Force | Out-Null

$LaunchRecord = [ordered]@{
    timestamp = (Get-Date).ToUniversalTime().ToString("o")
    date = $DateKey
    broker = "ALPACA"
    paper_only = $true
    maximum_daily_orders = $MaximumDailyOrders
    maximum_order_notional = $MaximumOrderNotional
    smart_safety_enforcement = $true
    maximum_daily_loss = 50
    maximum_consecutive_losses = 2
    maximum_open_positions = 2
    maximum_symbol_exposure = 500
    duplicate_symbol_buy_blocked = $true
    etrade_live_write_enabled = $false
}
Add-Content -Path (Join-Path $AuditDir "launch_ledger.jsonl") `
    -Value ($LaunchRecord | ConvertTo-Json -Compress) -Encoding UTF8

Write-Host "============================================"
Write-Host "ALPACA PAPER AUTOTRADING"
Write-Host "DATE: $DateKey"
Write-Host "MAXIMUM DAILY PAPER ORDERS: $MaximumDailyOrders"
Write-Host "MAXIMUM ORDER NOTIONAL: `$$MaximumOrderNotional"
Write-Host "DAILY LOSS LIMIT: -`$50"
Write-Host "CONSECUTIVE LOSS LIMIT: 2"
Write-Host "MAXIMUM OPEN POSITIONS: 2"
Write-Host "MAXIMUM SYMBOL EXPOSURE: `$$500"
Write-Host "DUPLICATE SYMBOL BUY: BLOCKED"
Write-Host "ETRADE LIVE WRITE: OFF"
Write-Host "============================================"

& $Python .\tools\run_paper_autonomous_daily_session.py `
    --repository-root $PSScriptRoot `
    --poll-seconds $PollSeconds `
    --maximum-daily-orders $MaximumDailyOrders `
    --maximum-order-notional $MaximumOrderNotional `
    --market-close-buffer-minutes $CloseBufferMinutes

$ExitCode = $LASTEXITCODE
$ExitRecord = [ordered]@{
    timestamp = (Get-Date).ToUniversalTime().ToString("o")
    date = $DateKey
    exit_code = $ExitCode
    broker = "ALPACA"
    paper_only = $true
    etrade_live_write_enabled = $false
}
Add-Content -Path (Join-Path $AuditDir "exit_ledger.jsonl") `
    -Value ($ExitRecord | ConvertTo-Json -Compress) -Encoding UTF8

exit $ExitCode