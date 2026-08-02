param(
    [string]$ClientOrderId = "single-60d3c5406e5226ae71d7"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== ACTUAL ALPACA PAPER ORDER/POSITION/ACCOUNT GET-ONLY READ ==="
Write-Host "No order submission, modification, or cancellation is possible."

if ($env:AI_STOCK_BOT_ENABLE_ACTUAL_FILL_RECONCILIATION_READ -ne "YES") {
    throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_FILL_RECONCILIATION_READ=YES"
}
if ($env:AI_STOCK_BOT_ACTUAL_FILL_RECONCILIATION_CONFIRMATION -ne "READ ACTUAL ALPACA PAPER ORDER POSITION ACCOUNT GET ONLY") {
    throw "Set the exact fill reconciliation confirmation text."
}

python tools/run_actual_order_lifecycle_fill_reconciliation_v128_01_to_v129_00.py `
    --repository-root . `
    --client-order-id $ClientOrderId
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "ACTUAL ORDER LIFECYCLE/FILL RECONCILIATION READ COMPLETE"
