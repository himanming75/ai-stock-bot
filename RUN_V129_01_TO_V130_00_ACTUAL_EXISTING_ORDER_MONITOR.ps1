param(
    [string]$ClientOrderId = "single-60d3c5406e5226ae71d7",
    [int]$MaxPolls = 3,
    [double]$PollIntervalSeconds = 5
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== ACTUAL ALPACA PAPER EXISTING ORDER MONITOR ==="
Write-Host "GET only. No order submission, replacement, modification, or cancellation."

if ($env:AI_STOCK_BOT_ENABLE_ACTUAL_LIFECYCLE_MONITOR -ne "YES") {
    throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_LIFECYCLE_MONITOR=YES"
}
if ($env:AI_STOCK_BOT_ACTUAL_LIFECYCLE_MONITOR_CONFIRMATION -ne "MONITOR ACTUAL ALPACA PAPER ORDER GET ONLY") {
    throw "Set the exact lifecycle monitor confirmation text."
}
if ($MaxPolls -lt 1 -or $MaxPolls -gt 20) {
    throw "MaxPolls must be between 1 and 20."
}
if ($PollIntervalSeconds -lt 0 -or $PollIntervalSeconds -gt 300) {
    throw "PollIntervalSeconds must be between 0 and 300."
}

python tools/run_actual_existing_paper_order_lifecycle_monitor_v129_01_to_v130_00.py `
    --repository-root . `
    --client-order-id $ClientOrderId `
    --max-polls $MaxPolls `
    --poll-interval-seconds $PollIntervalSeconds
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "ACTUAL EXISTING PAPER ORDER MONITOR COMPLETE"
