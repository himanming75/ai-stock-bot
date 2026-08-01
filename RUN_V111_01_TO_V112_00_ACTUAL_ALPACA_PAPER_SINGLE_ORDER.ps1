param(
    [Parameter(Mandatory=$true)][ValidateSet("AAPL","SPY","QQQ")][string]$Symbol,
    [Parameter(Mandatory=$true)][ValidateSet("buy","sell")][string]$Side,
    [Parameter(Mandatory=$true)][decimal]$Quantity,
    [Parameter(Mandatory=$true)][decimal]$ReferencePrice
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== ACTUAL ALPACA PAPER SINGLE-ORDER EXECUTION ==="
Write-Host "PAPER account only. Maximum one order, one share, and estimated notional of $100."
Write-Host "This command can submit a real order to your Alpaca PAPER account."

if ($env:AI_STOCK_BOT_ENABLE_ALPACA_PAPER_SINGLE_ORDER -ne "YES") {
    throw "Set AI_STOCK_BOT_ENABLE_ALPACA_PAPER_SINGLE_ORDER=YES"
}
if ($env:AI_STOCK_BOT_ALPACA_PAPER_ORDER_CONFIRMATION -ne "SUBMIT ONE ALPACA PAPER ORDER ONLY") {
    throw "Set the exact order confirmation text."
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY to PAPER credentials."
}
if ($Quantity -le 0 -or $Quantity -gt 1) {
    throw "Quantity must be greater than 0 and no more than 1."
}
if (($Quantity * $ReferencePrice) -gt 100) {
    throw "Estimated notional must be $100 or less."
}

python tools/run_actual_alpaca_paper_single_order_v111_01_to_v112_00.py `
    --repository-root . `
    --symbol $Symbol `
    --side $Side `
    --quantity $Quantity `
    --reference-price $ReferencePrice

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Remove-Item Env:AI_STOCK_BOT_ENABLE_ALPACA_PAPER_SINGLE_ORDER -ErrorAction SilentlyContinue
Remove-Item Env:AI_STOCK_BOT_ALPACA_PAPER_ORDER_CONFIRMATION -ErrorAction SilentlyContinue

Write-Host "ACTUAL ALPACA PAPER SINGLE-ORDER EXECUTION COMPLETE"
