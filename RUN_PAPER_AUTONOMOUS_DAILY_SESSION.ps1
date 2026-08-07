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

$PlanPath = Join-Path $PSScriptRoot "config\paper_validation_2week_300.json"
if(-not (Test-Path $PlanPath)) {
    throw "PAPER 2-WEEK VALIDATION PLAN NOT FOUND"
}
$Plan = Get-Content $PlanPath -Raw | ConvertFrom-Json

$Today = (Get-Date).Date
$DateKey = $Today.ToString("yyyy-MM-dd")
$DayPlan = $Plan.daily_entry_caps |
    Where-Object { $_.date -eq $DateKey } |
    Select-Object -First 1

if(-not $DayPlan) {
    Write-Host "PAPER VALIDATION WINDOW NOT ACTIVE FOR: $DateKey"
    Write-Host "NO NEW PAPER ENTRY WILL BE SUBMITTED."
    exit 0
}

$MaximumDailyOrders = [int]$DayPlan.maximum_daily_entries
$ValidationDay = [int]$DayPlan.day
$ValidationTarget = [int]$Plan.target_closed_trades

$env:PAPER_VALIDATION_TARGET_CLOSED_TRADES = "$ValidationTarget"
$env:PAPER_VALIDATION_BASELINE_PATH = Join-Path `
    $PSScriptRoot `
    "runtime\paper_validation_2week_300\baseline.json"

$MaximumOrderNotional = 100
$PollSeconds = 60
$CloseBufferMinutes = 15

$AuditDir = Join-Path $PSScriptRoot "runtime\paper_autotrading_ramp_v2"
New-Item -ItemType Directory -Path $AuditDir -Force | Out-Null

$LaunchRecord = [ordered]@{
    timestamp = (Get-Date).ToUniversalTime().ToString("o")
    date = $DateKey
    validation_id = $Plan.validation_id
    validation_day = $ValidationDay
    validation_target_closed_trades = $ValidationTarget
    broker = "ALPACA"
    paper_only = $true
    maximum_daily_orders = $MaximumDailyOrders
    maximum_order_notional = $MaximumOrderNotional
    smart_safety_enforcement = $true
    maximum_daily_loss = 50
    maximum_consecutive_losses = 2
    maximum_open_positions = 4
    maximum_symbol_exposure = 500
    duplicate_symbol_buy_blocked = $true
    etrade_live_write_enabled = $false
}
Add-Content -Path (Join-Path $AuditDir "launch_ledger.jsonl") `
    -Value ($LaunchRecord | ConvertTo-Json -Compress) -Encoding UTF8

Write-Host "============================================"
Write-Host "ALPACA PAPER AUTOTRADING"
Write-Host "DATE: $DateKey"
Write-Host "VALIDATION DAY: $ValidationDay / 10"
Write-Host "CLOSED TRADE TARGET: $ValidationTarget"
Write-Host "MAXIMUM DAILY PAPER ENTRIES: $MaximumDailyOrders"
Write-Host "MAXIMUM ORDER NOTIONAL: `$$MaximumOrderNotional"
Write-Host "DAILY LOSS LIMIT: -`$50"
Write-Host "CONSECUTIVE LOSS LIMIT: 2"
Write-Host "MAXIMUM OPEN POSITIONS: 4"
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