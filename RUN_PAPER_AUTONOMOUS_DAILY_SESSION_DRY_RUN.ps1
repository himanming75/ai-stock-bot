[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)) {
    throw "PROJECT VIRTUAL ENVIRONMENT PYTHON NOT FOUND"
}

$env:APCA_API_KEY_ID = [Environment]::GetEnvironmentVariable(
    "APCA_API_KEY_ID",
    "User"
)
$env:APCA_API_SECRET_KEY = [Environment]::GetEnvironmentVariable(
    "APCA_API_SECRET_KEY",
    "User"
)
$env:LIVE_TRADING_ENABLED = "false"
$env:ETRADE_LIVE_WRITE_ENABLED = "false"
$env:ETRADE_LIVE_SUBMISSION_ENABLED = "false"

& $Python `
    .\tools\run_paper_autonomous_daily_session.py `
    --repository-root $PSScriptRoot `
    --poll-seconds 15 `
    --maximum-daily-orders 1 `
    --maximum-order-notional 100 `
    --market-close-buffer-minutes 15 `
    --dry-run

exit $LASTEXITCODE
