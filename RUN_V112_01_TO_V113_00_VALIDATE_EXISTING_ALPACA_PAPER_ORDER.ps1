param(
    [Parameter(Mandatory=$true)][string]$ClientOrderId,
    [int]$MaxPollAttempts = 5,
    [double]$PollIntervalSeconds = 1
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== EXISTING ALPACA PAPER ORDER READ-ONLY VALIDATION ==="
Write-Host "This script cannot submit or cancel orders."

if ($env:AI_STOCK_BOT_ENABLE_ALPACA_PAPER_ORDER_VALIDATION -ne "YES") {
    throw "Set AI_STOCK_BOT_ENABLE_ALPACA_PAPER_ORDER_VALIDATION=YES"
}
if ($env:AI_STOCK_BOT_ALPACA_PAPER_ORDER_VALIDATION_CONFIRMATION -ne "VALIDATE ONE EXISTING ALPACA PAPER ORDER ONLY") {
    throw "Set the exact validation confirmation text."
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY to PAPER credentials."
}
if (-not $ClientOrderId.StartsWith("BOT-PAPER-ONE-")) {
    throw "ClientOrderId must begin with BOT-PAPER-ONE-"
}

python tools/run_actual_alpaca_paper_order_validation_v112_01_to_v113_00.py `
    --repository-root . `
    --client-order-id $ClientOrderId `
    --max-poll-attempts $MaxPollAttempts `
    --poll-interval-seconds $PollIntervalSeconds

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "EXISTING ALPACA PAPER ORDER VALIDATION COMPLETE"
